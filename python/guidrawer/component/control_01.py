#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import pymel.core as pm

from . import AbstractComponentGuide


class ComponentGuide(AbstractComponentGuide):
    order = 0
    componentType = "control_01"
    name = "control_01"
    """
    Draw control_01 guide structure.
    """
    @classmethod
    def draw_guide(cls,
                   name,
                   comp_guide,
                   side,
                   idx,
                   parentRoot):
        pm.select(cl=True)
        if not name:
            name = "control"

        # set valid index
        comp_guide.setIndex(pm.PyNode("guide"))

        # main guide
        comp_guide.draw(parentRoot)
        guide_name = pm.ls(sl=True)[0]

        comp_guide.rename(guide_name, name, side, idx)
        guide_root = pm.ls(sl=True)[0]

        return guide_root
