class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""
    pass


class UrlNotFoundException(Exception):
    """Вызывается при ошибке обработки URL."""
    pass
