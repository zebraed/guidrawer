#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from functools import wraps

from maya import cmds

from . import exception


def undo(func):
    @wraps(func)
    def _undofunc(*args, **kwargs):
        try:
            # start an undo chunk
            cmds.undoInfo(ock=True)
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(cck=True)
    return _undofunc


def check_comp_condition(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            raise exception.ComponentImportError("component base directory not found.")
    return _wrapper
