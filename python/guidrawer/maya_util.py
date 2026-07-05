from maya import OpenMayaUI as omui

from mgear.vendor.Qt import QtWidgets


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
