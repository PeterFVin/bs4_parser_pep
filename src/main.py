from collections import defaultdict
import logging
import re

from bs4 import BeautifulSoup
import requests_cache
from tqdm import tqdm
from urllib.parse import urljoin

from constants import (BASE_DIR,
                       DOWNLOADS_DIR,
                       EXPECTED_STATUS,
                       MAIN_DOC_URL,
                       MAIN_PEP_URL)
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from phrazes import (ARGUMENTS,
                     DOWNLOAD_ARCHIVE,
                     EXCEPTION_TEXT,
                     PARSER_OFF,
                     PARSER_ON,
                     VALUEERROR,
                     WRONG_STATUSES_BODY,
                     WRONG_STATUSES_END,
                     WRONG_STATUSES_HEAD)
from utils import find_tag, get_response

WHATS_NEW_URL = urljoin(MAIN_DOC_URL, 'whatsnew/')


def get_soup(response):
    return BeautifulSoup(response.text, features='lxml')


def whats_new(session):
    response = get_response(session, WHATS_NEW_URL)
    if response is None:
        return
    sections_by_python = get_soup(response).select('#what-s-new-in-python ' +
                                                   'div.toctree-wrapper ' +
                                                   'li.toctree-l1')
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(WHATS_NEW_URL, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        h1 = find_tag(get_soup(response), 'h1')
        dl = get_soup(response).find('dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    sidebar = get_soup(response).find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ValueError(VALUEERROR)
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
    response = get_response(session, downloads_url)
    if response is None:
        return
    response.encoding = 'utf-8'
    table_tag = get_soup(response).select_one('div[role="main"] ' +
                                              'table.docutils')
    pdf_a4_link = table_tag.find('a',
                                 href=re.compile(r'.+pdf-a4\.zip$'))['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    archive_path = DOWNLOADS_DIR / filename
    response = session.get(archive_url)
    logging.info(DOWNLOAD_ARCHIVE.format(archive_path))

    with open(archive_path, 'wb') as file:
        file.write(response.content)


def pep(session):
    try:
        response = get_response(session, MAIN_PEP_URL)
        if response is None:
            return
        section = get_soup(response).find('section', {'id': 'numerical-index'})
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
            response = get_response(session, pep_link)
            if response is None:
                return
            section = get_soup(response).find('section', {'id': 'pep-content'})
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
    except Exception as Argument:
        logging.exception(EXCEPTION_TEXT.format(Argument))


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
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


if __name__ == '__main__':
    main()
