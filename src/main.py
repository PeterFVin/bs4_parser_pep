from collections import defaultdict
import logging
import re

from bs4 import BeautifulSoup
import requests_cache
from tqdm import tqdm
from urllib.parse import urljoin

from exceptions import ParserFindTagException, UrlNotFoundException
from constants import (BASE_DIR,
                       EXPECTED_STATUS,
                       MAIN_DOC_URL,
                       MAIN_PEP_URL)
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import find_tag, get_response


ARGUMENTS = 'Аргументы командной строки: {}'
DOWNLOAD_ARCHIVE = 'Архив был загружен и сохранён: {}'
DOWNLOADS_DIR = BASE_DIR / 'downloads'
EXCEPTION_TEXT = 'Возникло исключение: {}'
PARSER_OFF = 'Парсер завершил работу.'
PARSER_ON = 'Парсер запущен!'
TAG_FIND_ERROR = 'Тег {} не найден!'
TAG_TEXT_FIND_ERROR = 'All versions не найден!'
URL_ERROR_TEXT = 'Не удалось обработать url {}: {}'
WHATS_NEW_URL = urljoin(MAIN_DOC_URL, 'whatsnew/')
WRONG_STATUSES_BODY = '\n{}\nСтатус в карточке: {}\nОжидаемые статусы: {}'
WRONG_STATUSES_END = '\nНесовпадающие статусы отсутствуют!'
WRONG_STATUSES_HEAD = 'Несовпадающие статусы:'


def get_soup(session, url, features='lxml'):
    response = get_response(session, url)
    response.encoding = 'utf-8'
    if response is None:
        return
    return BeautifulSoup(response.text, features=features)


def whats_new(session):
    a_tags = (get_soup(
        session,
        url=WHATS_NEW_URL).select(
            '#what-s-new-in-python div.toctree-wrapper li.toctree-l1 > a'))
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for a_tag in tqdm(a_tags):
        href = a_tag['href']
        version_link = urljoin(WHATS_NEW_URL, href)
        try:
            h1 = find_tag(get_soup(session, url=version_link), 'h1')
            if h1 is None:
                raise ParserFindTagException(TAG_FIND_ERROR.format(h1))
            dl = get_soup(session, url=version_link).find('dl')
            if dl is None:
                raise ParserFindTagException(TAG_FIND_ERROR.format(dl))
        except UrlNotFoundException as e:
            logging.error(URL_ERROR_TEXT.format(version_link, e))
            continue
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    sidebar = get_soup(session, url=MAIN_DOC_URL).find(
        'div',
        {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise ParserFindTagException(TAG_TEXT_FIND_ERROR)
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    for a_tag in a_tags:
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (a_tag['href'], version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    table_tag = get_soup(session, url=downloads_url).select_one(
        'div[role="main"] table.docutils')
    pdf_a4_link = table_tag.find('a',
                                 href=re.compile(r'.+pdf-a4\.zip$'))['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    DOWNLOADS_DIR = BASE_DIR / 'downloads'
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    archive_path = DOWNLOADS_DIR / filename
    response = session.get(archive_url)
    logging.info(DOWNLOAD_ARCHIVE.format(archive_path))

    with open(archive_path, 'wb') as file:
        file.write(response.content)


def pep(session):
    section = get_soup(session, url=MAIN_PEP_URL).find(
        'section',
        {'id': 'numerical-index'})
    table = section.find(
        'table',
        {'class': 'pep-zero-table docutils align-default'},
        )
    tbody = table.find('tbody')
    tr_tags = tbody.find_all('tr')
    results = defaultdict(int)
    logging_message = WRONG_STATUSES_HEAD
    errors_counter = 0
    for tr in tr_tags:
        td = tr.find_all('td')
        status_letter = (td[0].text[1]) if len(td[0].text) > 1 else ''
        a_tag = tr.find('a')
        pep_link = urljoin(MAIN_PEP_URL, a_tag['href'])
        try:
            section = get_soup(session, pep_link).find(
                'section',
                {'id': 'pep-content'})
            if section is None:
                raise ParserFindTagException(TAG_FIND_ERROR.format(section))
        except UrlNotFoundException as e:
            logging.error(URL_ERROR_TEXT.format(pep_link, e))
            continue
        dt_tags = section.find_all('dt')
        for dt in dt_tags:
            if dt.get_text(strip=True) == 'Status:':
                status_value = dt.find_next_sibling('dd').get_text(
                    strip=True)
        if status_value not in EXPECTED_STATUS[status_letter]:
            logging_message += (
                WRONG_STATUSES_BODY.format(
                    pep_link,
                    status_value,
                    EXPECTED_STATUS[status_letter]))
            errors_counter += 1
        results[status_value] += 1
    if errors_counter == 0:
        logging_message += WRONG_STATUSES_END
    logging.info(logging_message)
    return [
        ('Статус', 'Количество'),
        *results.items(),
        ('Всего', sum(results.values())),
    ]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    try:
        configure_logging()
        logging.info(PARSER_ON)
        arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = arg_parser.parse_args()
        logging.info(ARGUMENTS.format(args))
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
        logging.info(PARSER_OFF)
    except Exception as Argument:
        logging.exception(EXCEPTION_TEXT.format(Argument))


if __name__ == '__main__':
    main()
