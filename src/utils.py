from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from exceptions import ParserFindTagException

ERROR_MESSAGE = 'Не найден тег {} {}'
ERROR_TEXT = 'Возникла ошибка при загрузке страницы {}: {}'


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException as e:
        raise RuntimeError(ERROR_TEXT.format(url, e))


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_message = ERROR_MESSAGE.format(tag, attrs)
        raise ParserFindTagException(error_message)
    return searched_tag


def get_soup(session, url, features='lxml'):
    return BeautifulSoup(get_response(session, url).text, features=features)
