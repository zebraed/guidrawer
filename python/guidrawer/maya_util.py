from typing import Callable, Optional

from maya import OpenMaya as om
from maya import OpenMayaUI as omui

from mgear.vendor.Qt import QtWidgets


class MayaError(BaseException):
    """Base exception for Maya-related errors."""


class MayaAPIError(MayaError):
    """Error with Maya API operations."""


class MayaEventWatcher:
    """Manage Maya event callbacks using OpenMaya."""

    def __init__(self, event_name: str, update_fn: Callable[[], None]):
        self._event_name: str = event_name
        self._update_fn: Callable[[], None] = update_fn
        self._cb_id: Optional[int] = None

    def _on_event(self, *_args):
        try:
            if callable(self._update_fn):
                self._update_fn()
        except Exception as e:
            raise MayaAPIError(
                f"Failed to call update function: {e}"
            ) from e

    def start(self) -> bool:
        """Install the event callback if not already started."""
        if self._cb_id is not None:
            return True

        try:
            self._cb_id = om.MEventMessage.addEventCallback(
                self._event_name, self._on_event
            )
            return True
        except Exception as e:
            self._cb_id = None
            raise MayaAPIError(
                f"Failed to install event callback: {e}"
            ) from e

    def stop(self) -> None:
        """Remove the event callback if present."""
        if self._cb_id is None:
            return
        om.MMessage.removeCallback(self._cb_id)
        self._cb_id = None


def get_maya_main_window():
    """Get the main window of Maya."""
    try:
        from shiboken6 import wrapInstance
    except ImportError:
        from shiboken2 import wrapInstance

    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is None:
        return None
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
