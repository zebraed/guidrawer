from maya import cmds
import mgear.pymaya as pm

from . import AbstractComponentGuide


class ComponentGuide(AbstractComponentGuide):
    order = 20
    componentType = "control_01"
    name = "two_control_01"
    """Example of a custom guide drawer class for two-layer control_01 component."""

    @classmethod
    def draw_guide(cls, name, comp_guide, side, idx, parent_root):
        def _set_attr(guide):
            cmds.setAttr(f"{guide}.joint", False)
            cmds.setAttr(f"{guide}.neutralRotation", False)
            cmds.setAttr(f"{guide}.ctlSize", 0.7)

        cmds.select(cl=True)

        comp_guide.setIndex(pm.PyNode("guide"))

        comp_guide.draw(parent_root)
        guide_name = cmds.ls(sl=True)[0]
        _set_attr(guide_name)
        cmds.setAttr(f"{guide_name}.icon", "square", type="string")

        comp_guide.rename(guide_name, "offset", side, idx)
        guide_root = cmds.ls(sl=True)[0]
        cmds.select(cl=True)

        comp_guide.setIndex(pm.PyNode("guide"))
        parent_root = guide_root
        comp_guide.draw(parent_root)
        offset_root_guide = cmds.ls(sl=True)[0]
        _set_attr(offset_root_guide)

        cmds.select(cl=True)

        cmds.setAttr(f"{offset_root_guide}.icon", "diamond", type="string")
        cmds.setAttr(f"{offset_root_guide}.ctlSize", 0.5)

        comp_guide.rename(offset_root_guide, "subOffset", side, idx)
        return guide_root
