import os

from maya import cmds
import mgear


STR_CMD = """
import guidrawer
guidrawer.showUI()
"""

_ICON_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "ui",
    "icons",
    "guidrawer_icon.svg",
)
_MENU_ITEM = "guidrawer_mgear_menuItem"


def mGear_add_menu():
    if cmds.menuItem(_MENU_ITEM, exists=True):
        return

    cmds.setParent(mgear.menu_id, menu=True)
    cmds.menuItem(divider=True)
    cmds.menuItem(
        _MENU_ITEM,
        label="Guidrawer",
        command=STR_CMD,
        image=_ICON_PATH,
    )
