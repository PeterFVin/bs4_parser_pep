from exceptions import ParserFindTagException
from requests import RequestException

from phrazes import ERROR_MESSAGE, REQUEST_EXCEPTION_TEXT


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException:
        raise RequestException(REQUEST_EXCEPTION_TEXT.format(url))


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_message = ERROR_MESSAGE.format(tag, attrs)
        raise ParserFindTagException(error_message)
    return searched_tag
