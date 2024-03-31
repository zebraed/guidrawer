#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8


class ComponentImportError(Exception):
    def __init__(self, message):
        super(ComponentImportError, self).__init__(message)


class ComponentNotFoundError(Exception):
    def __init__(self, message):
        super(ComponentNotFoundError, self).__init__(message)


class NotLoadedError(Exception):
    def __init__(self, message):
        super(NotLoadedError, self).__init__(message)


class NotExistError(Exception):
    def __init__(self, message):
        super(NotExistError, self).__init__(message)
