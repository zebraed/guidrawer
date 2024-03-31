#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import pymel.core as pm

from . import AbstractComponentGuide


class ComponentGuide(AbstractComponentGuide):
    order = 20
    componentType = "control_01"
    name = "two_control_01"

    """Example of a custom guide drawer class for two-layer control_01 component.
    """
    @classmethod
    def draw_guide(cls,
                   name,
                   comp_guide,
                   side,
                   idx,
                   parentRoot):
        def _set_attr(guide):
            pm.setAttr(guide + ".joint", False)
            pm.setAttr(guide + ".neutralRotation", False)
            pm.setAttr(guide + ".ctlSize", 0.7)

        pm.select(cl=True)

        # set valid index
        comp_guide.setIndex(pm.PyNode("guide"))

        # main guide
        comp_guide.draw(parentRoot)
        guide_name = pm.ls(sl=True)[0]
        _set_attr(guide_name)
        pm.setAttr(guide_name + ".icon", "square", type="string")

        # override guide name.
        comp_guide.rename(guide_name, "offset", side, idx)
        guide_root = pm.ls(sl=True)[0]
        pm.select(cl=True)

        # offset guide
        comp_guide.setIndex(pm.PyNode("guide"))
        parentRoot = guide_root
        comp_guide.draw(parentRoot)
        offset_root_guide = pm.ls(sl=True)[0]
        _set_attr(offset_root_guide)

        pm.select(cl=True)

        pm.setAttr(offset_root_guide + '.icon', "diamond", type="string")
        pm.setAttr(offset_root_guide + ".ctlSize", 0.5)

        comp_guide.rename(offset_root_guide, "subOffset", side, idx)
        return guide_root
