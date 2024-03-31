#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import pymel.core as pm

from . import AbstractComponentGuide


class ComponentGuide(AbstractComponentGuide):
    order = 4
    componentType = "chain_spring_01"
    name = "chain_spring_01"
    """
    Draw chin_spring_01 guide structure
    """
    # if True, the custom_modalPositions method will be called.
    override_modalPositions = True

    @classmethod
    def draw_guide(cls,
                   name,
                   comp_guide,
                   side,
                   idx,
                   parentRoot,
                   **opt):
        pm.select(cl=True)
        if not name:
            name = "chainSpring"
        comp_node_list = list()
        parent_root = pm.PyNode(parentRoot)
        comp_guide.setIndex(pm.PyNode("guide"))

        sections_number = opt.get("sections_number", 5)
        dir_axis = opt.get("dir_axis", 0)
        spacing = opt.get("spacing", 0.5)

        while True:
            if parent_root.hasAttr("ismodel"):
                break

            if parent_root.hasAttr("comp_type"):
                parent_type = parent_root.attr("comp_type").get()
                parent_side = parent_root.attr("comp_side").get()
                parent_uihost = parent_root.attr("ui_host").get()
                parent_ctlGrp = parent_root.attr("ctlGrp").get()

                if parent_type in comp_guide.connectors:
                    comp_guide.setParamDefValue("connector", parent_type)

                comp_guide.setParamDefValue("comp_side", side)
                comp_guide.setParamDefValue("ui_host", parent_uihost)
                comp_guide.setParamDefValue("ctlGrp", parent_ctlGrp)
                break
        comp_guide.modalPositions(sections_number, dir_axis, spacing)
        comp_guide.drawFromUI(parent_root, showUI=False)
        guide_root = pm.ls(sl=True)[0]
        comp_guide.rename(guide_root, name, side, idx)
        pm.setAttr(guide_root + ".comp_name", name, type="string")
        pm.setAttr(guide_root + ".comp_side", side, type="string")
        pm.setAttr(guide_root + ".ui_host",   parentRoot, type="string")
        for comp_node in pm.ls(guide_root, dag=True, tr=True):
            comp_node = pm.rename(comp_node, comp_node.replace(cls.componentType,
                                                               name))
            if "_root" in comp_node or "_loc" in comp_node:
                comp_node_list.append(comp_node)

        return guide_root
