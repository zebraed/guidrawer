__author__ = "zebraed"
__description__ = "mGear Guide Drawer Tools"
__version__ = "3.2.0"
__license__ = "MIT"
__copyright__ = "Copyright 2022-2026 zebraed"


def showUI(*args):
    """Open the Guidrawer UI."""
    from .ui import show as _show_ui
    return _show_ui(*args)


def Reload():
    """Reload all the modules."""
    import sys

    for k in list(sys.modules):
        if k.startswith(__name__):
            del sys.modules[k]
    print(f"{__name__} Reloaded.")


__all__ = ["Reload", "showUI"]
