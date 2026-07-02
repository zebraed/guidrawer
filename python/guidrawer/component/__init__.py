from maya import cmds
import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.core import string
from mgear.core import transform


class AbstractComponentGuide:
    order = None
    componentType = None
    name = "base"

    @classmethod
    def draw_guide(
        cls,
        comp_guide,
        name,
        side,
        idx,
        parent_root,
    ):
        """Virtual func."""
        cmds.select(cl=True)

        comp_guide.setIndex(pm.PyNode("guide"))

        comp_guide.draw(parent_root)
        guide_name = cmds.ls(sl=True)[0]
        comp_guide.rename(guide_name, name, side, idx)
        new_guide_name = cmds.ls(sl=True)[0]
        return new_guide_name

    def custom_modalPositions(
        self, sections_number=None, dir_axis=None, spacing=None
    ):
        self.sections_number = sections_number
        self.dir_axis = dir_axis
        self.spacing = spacing
        for name in self.save_transform:
            if "#" in name:
                if sections_number:
                    if dir_axis == 0:
                        off_vec = datatypes.Vector(spacing, 0, 0)
                    elif dir_axis == 3:
                        off_vec = datatypes.Vector(spacing * -1, 0, 0)
                    elif dir_axis == 1:
                        off_vec = datatypes.Vector(0, spacing, 0)
                    elif dir_axis == 4:
                        off_vec = datatypes.Vector(0, spacing * -1, 0)
                    elif dir_axis == 2:
                        off_vec = datatypes.Vector(0, 0, spacing)
                    elif dir_axis == 5:
                        off_vec = datatypes.Vector(0, 0, spacing * -1)

                    new_position = datatypes.Vector(0, 0, 0)
                    for i in range(sections_number):
                        new_position = off_vec + new_position
                        local_name = string.replaceSharpWithPadding(name, i)
                        self.tra[local_name] = transform.getTransformFromPos(
                            new_position
                        )
        return True
