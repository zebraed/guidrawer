__author__ = "zebraed"
__version__ = "2.0.0"
__license__ = "MIT"
__copyright__ = "Copyright 2022-2026 zebraed"


from .ui import showUI


def Reload():
    """
    Reload all the modules.
    """
    import sys
    for k in list(sys.modules):
        if k.startswith(__name__):
            del sys.modules[k]
    print(__name__ + " Reloaded.")


__all__ = ["Reload", "showUI"]
