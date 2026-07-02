from maya import cmds
import mgear


STR_GUIDRAWER = """
from guidrawer import ui
ui.show()
"""


def mGear_add_menu():
    cmds.setParent(mgear.menu_id, menu=True)
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Guidrawer", command=STR_GUIDRAWER)
