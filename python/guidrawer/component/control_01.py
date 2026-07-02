from maya import cmds
import mgear.pymaya as pm

from . import AbstractComponentGuide


class ComponentGuide(AbstractComponentGuide):
    order = 0
    componentType = "control_01"
    name = "control_01"
    """Draw control_01 guide structure."""

    @classmethod
    def draw_guide(cls, name, comp_guide, side, idx, parent_root):
        cmds.select(cl=True)
        if not name:
            name = "control"

        comp_guide.setIndex(pm.PyNode("guide"))

        comp_guide.draw(parent_root)
        guide_name = cmds.ls(sl=True)[0]

        comp_guide.rename(guide_name, name, side, idx)
        guide_root = cmds.ls(sl=True)[0]

        return guide_root
