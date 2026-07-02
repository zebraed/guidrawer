
class ComponentImportError(Exception):
    def __init__(self, message):
        super().__init__(message)


class ComponentNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NotLoadedError(Exception):
    def __init__(self, message):
        super().__init__(message)


class NotExistError(Exception):
    def __init__(self, message):
        super().__init__(message)
