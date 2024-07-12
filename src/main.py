from bs4 import BeautifulSoup
import logging
import re
import requests_cache
from tqdm import tqdm
from urllib.parse import urljoin

from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, MAIN_PEP_URL
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import find_tag, get_response

whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')


def whats_new(session):
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')

    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})

    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})

    sections_by_python = div_with_ul.find_all(
        'li',
        attrs={'class': 'toctree-l1'})

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]

    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = soup.find('dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')

    sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    print(MAIN_DOC_URL)
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    for a_tag in a_tags:
        link = a_tag['href']
        text = a_tag.text
        text_match = re.search(pattern, text)
        match text_match:
            case re.Match():
                version, status = text_match.group(1, 2)
                results.append(
                    (link, version, status)
                    )
            case _:
                version = text
                status = ''
                results.append(
                    (link, version, status)
                    )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = soup.find('div', {'role': 'main'})
    table_tag = main_tag.find('table', {'class': 'docutils'})
    pdf_a4_tag = table_tag.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')

    with open(archive_path, 'wb') as file:
        file.write(response.content)


def pep(session):
    response = get_response(session, MAIN_PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    section = soup.find('section', {'id': 'numerical-index'})
    table = section.find(
        'table',
        {'class': 'pep-zero-table docutils align-default'},
        )
    tbody = table.find('tbody')
    tr_tags = tbody.find_all('tr')
    results = {}
    logging.info('Несовпадающие статусы:')
    for tr in tr_tags:
        td = tr.find_all('td')
        status_letter = (td[0].text[1]) if len(td[0].text) > 1 else ''
        a_tag = tr.find('a')
        pep_link = urljoin(MAIN_PEP_URL, a_tag['href'])
        response = get_response(session, pep_link)
        if response is None:
            return
        pep_soup = BeautifulSoup(response.text, features='lxml')
        section = pep_soup.find('section', {'id': 'pep-content'})
        dt_tags = section.find_all('dt')
        for dt in dt_tags:
            if dt.get_text(strip=True) == 'Status:':
                status_value = dt.find_next_sibling('dd').get_text(strip=True)

        errors_counter = 0
        if status_value not in EXPECTED_STATUS[status_letter]:
            logging.info(
                f'{pep_link}\n' +
                f'Статус в карточке: {status_value}\n' +
                f'Ожидаемые статусы: {EXPECTED_STATUS[status_letter]}')
            errors_counter += 1

        if status_value not in results:
            results[status_value] = 1
        else:
            results[status_value] += 1
    if errors_counter == 0:
        logging.info('Несовпадающие статусы отсутствуют!')
    results['Total'] = sum(results.values())
    results = list(results.items())
    results.insert(0, ('Статус', 'Количество'))
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
