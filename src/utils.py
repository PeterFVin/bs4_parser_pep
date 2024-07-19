from exceptions import ParserFindTagException

ERROR_MESSAGE = 'Не найден тег {} {}'
REQUEST_EXCEPTION_TEXT = 'Возникла ошибка при загрузке страницы {}: {}'


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RuntimeError as e:
        raise RuntimeError(REQUEST_EXCEPTION_TEXT.format(url, e))


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_message = ERROR_MESSAGE.format(tag, attrs)
        raise ParserFindTagException(error_message)
    return searched_tag
