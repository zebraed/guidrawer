from maya import cmds
import mgear.pymaya as pm

from . import AbstractComponentGuide


class ComponentGuide(AbstractComponentGuide):
    order = 4
    componentType = "chain_spring_01"
    name = "chain_spring_01"
    """Draw chain_spring_01 guide structure."""
    override_modalPositions = True

    @classmethod
    def draw_guide(cls, name, comp_guide, side, idx, parent_root, **opt):
        cmds.select(cl=True)
        if not name:
            name = "chainSpring"
        comp_node_list = []
        parent_root_node = pm.PyNode(parent_root)
        comp_guide.setIndex(pm.PyNode("guide"))

        sections_number = opt.get("sections_number", 5)
        dir_axis = opt.get("dir_axis", 0)
        spacing = opt.get("spacing", 0.5)

        while True:
            if parent_root_node.hasAttr("ismodel"):
                break

            if parent_root_node.hasAttr("comp_type"):
                parent_type = parent_root_node.attr("comp_type").get()
                parent_side = parent_root_node.attr("comp_side").get()
                parent_uihost = parent_root_node.attr("ui_host").get()
                parent_ctl_grp = parent_root_node.attr("ctlGrp").get()

                if parent_type in comp_guide.connectors:
                    comp_guide.setParamDefValue("connector", parent_type)

                comp_guide.setParamDefValue("comp_side", side)
                comp_guide.setParamDefValue("ui_host", parent_uihost)
                comp_guide.setParamDefValue("ctlGrp", parent_ctl_grp)
                break

            next_parent = parent_root_node.getParent()
            if next_parent is None:
                break
            parent_root_node = next_parent

        comp_guide.modalPositions(sections_number, dir_axis, spacing)
        comp_guide.drawFromUI(parent_root_node, showUI=False)
        guide_root = cmds.ls(sl=True)[0]
        comp_guide.rename(guide_root, name, side, idx)
        cmds.setAttr(f"{guide_root}.comp_name", name, type="string")
        cmds.setAttr(f"{guide_root}.comp_side", side, type="string")
        cmds.setAttr(f"{guide_root}.ui_host", parent_root, type="string")
        for comp_node in cmds.ls(guide_root, dag=True, type="transform"):
            comp_node = cmds.rename(
                comp_node,
                comp_node.replace(cls.componentType, name),
            )
            if "_root" in comp_node or "_loc" in comp_node:
                comp_node_list.append(comp_node)

        return guide_root
