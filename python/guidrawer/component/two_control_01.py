"""Example preset that draws control_01 in two stacked layers."""
from maya import cmds

from .. import shifter_bridge as bridge

NAME = "two_control_01"
COMPONENT_TYPE = "control_01"
ORDER = 20


def _set_common_attr(guide_root):
    cmds.setAttr(f"{guide_root}.joint", False)
    cmds.setAttr(f"{guide_root}.neutralRotation", False)
    cmds.setAttr(f"{guide_root}.ctlSize", 0.7)


def draw_guide(name, side, idx, parent_root, **opt):
    if not name:
        name = bridge.get_default_name(COMPONENT_TYPE)
    sub_name = f"{name}Sub"

    # Main guide
    guide_root = bridge.draw_component(parent_root, COMPONENT_TYPE)
    _set_common_attr(guide_root)
    cmds.setAttr(f"{guide_root}.icon", "square", type="string")
    guide_root = bridge.rename_component(guide_root, name, side, idx)

    # Sub guide
    sub_root = bridge.draw_component(guide_root, COMPONENT_TYPE)
    _set_common_attr(sub_root)
    cmds.setAttr(f"{sub_root}.icon", "diamond", type="string")
    cmds.setAttr(f"{sub_root}.ctlSize", 0.5)
    bridge.rename_component(sub_root, sub_name, side, idx)

    cmds.select(cl=True)
    return guide_root
