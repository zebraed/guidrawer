#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import pymel.core as pm
from pymel.core import datatypes

from mgear.core import string
from mgear.core import transform


class AbstractComponentGuide(object):
    order = None
    componentType = None
    name = "base"

    @classmethod
    def draw_guide(cls,
                   comp_guide,
                   name,
                   side,
                   idx,
                   parentRoot,
                   ):
        """
        virtual func.
        """
        pm.select(cl=True)

        # set valid index
        comp_guide.setIndex(pm.PyNode("guide"))

        # draw guide
        comp_guide.draw(parentRoot)
        guide_name = pm.ls(sl=True)[0]
        comp_guide.rename(guide_name, name, side, idx)
        new_guide_name = pm.ls(sl=True)[0]
        return new_guide_name

    def custom_modalPositions(self, sections_number=None, dir_axis=None, spacing=None):
        self.sections_number = sections_number
        self.dir_axis = dir_axis
        self.spacing = spacing
        for name in self.save_transform:
            if "#" in name:
                if sections_number:
                    if dir_axis == 0:  # X
                        offVec = datatypes.Vector(spacing, 0, 0)
                    elif dir_axis == 3:  # -X
                        offVec = datatypes.Vector(spacing * -1, 0, 0)
                    elif dir_axis == 1:  # Y
                        offVec = datatypes.Vector(0, spacing, 0)
                    elif dir_axis == 4:  # -Y
                        offVec = datatypes.Vector(0, spacing * -1, 0)
                    elif dir_axis == 2:  # Z
                        offVec = datatypes.Vector(0, 0, spacing)
                    elif dir_axis == 5:  # -Z
                        offVec = datatypes.Vector(0, 0, spacing * -1)

                    newPosition = datatypes.Vector(0, 0, 0)
                    for i in range(sections_number):
                        newPosition = offVec + newPosition
                        localName = string.replaceSharpWithPadding(name, i)
                        self.tra[localName] = transform.getTransformFromPos(
                            newPosition)
        return True
