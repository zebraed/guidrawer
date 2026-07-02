from functools import wraps

from maya import cmds


def undo(func):
    @wraps(func)
    def _undofunc(*args, **kwargs):
        try:
            cmds.undoInfo(ock=True)
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(cck=True)
    return _undofunc
