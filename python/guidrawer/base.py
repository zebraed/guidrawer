#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from maya import cmds
import pymel.core as pm

try:
    import mgear.maya.transform as tra
    import mgear.maya.icon as ico
except:
    import mgear.core.transform as tra
    import mgear.core.icon as ico

import mgear.shifter

from . import decorator
from . import exception


class GuidrawerBase(object):
    def __init__(self):
        super(GuidrawerBase, self).__init__()
        self.guide_list = list()

    @classmethod
    def vaildate_guide(cls, root):
        """Validates the guide and returns the root node if it passes the validation.

        Args:
            root (str): The name of the root node.

        Returns:
            str: The validated root node.

        Raises:
            None

        Example:
            root_node = GuidrawerBase.vaildate_guide(ROOT_NODE_NAME)
        """
        if pm.objExists(root + ".isGearGuide"):
            if pm.getAttr(root + ".isGearGuide"):
                root = pm.PyNode(root)
            else:
                pm.warning("{} is guide. but not check on .isGearGuide".format(root))
                return
        else:
            if pm.objExists(root + ".ismodel"):
                #pm.warning("{} is guide top.".format(root))
                return pm.PyNode(root)

        return root

    @classmethod
    def get_root_from_selection(self):
        """Returns the root node from the current selection.

        The function retrieves the root node from the current selection
        by splitting the selection path and iterating through the nodes.
        It checks if each node has a 'comp_type' attribute and
        returns the first node that satisfies this condition.
        If no root node is found, it returns None.

        Returns:
            str or None: The root node from the current selection,
                or None if no root node is found.
        """
        fp = cmds.ls(sl=True, l=True)[0].split("|")
        for i in range(len(fp) - 1):
            a_l = list()
            if i == 0:
                a_l = fp[1:]
            else:
                a_l = fp[1:-i]
            node = "|".join(a_l)
            if node.find('_root'):
                if cmds.objExists(node + ".comp_type"):
                    return node
        return None

    @classmethod
    def create_temporary_group(cls, partsName):
        """
        Create temporary dammy group.
        """
        return cmds.group(n=partsName + "_tempGp#", em=True)

    @classmethod
    def draw_component(cls, parent, componentType):
        """
        Draw guide component from string name.

        Args:
            parent (str): parent object.
            componentType (str): draw new componet name.
            root (str, optional): target root. Defaults to None.

        Returns:
            str: new guide root name from selection list.

        Example:
            mgear.shifter.guide.Rig().drawNewComponent(parent=pm.PyNode("softmodRoot_C0_root"),
                                           comp_type="control_01", showUI=False)
        """
        if parent is not None:
            if pm.objExists(parent):
                parent = pm.PyNode(parent)
            else:
                raise exception.NotExistError("Parent object is not exists.")
        mgear.shifter.guide.Rig().drawNewComponent(parent, componentType,
                                                   showUI=False)
        newRoot = cmds.ls(sl=True)[0]
        cmds.select(cl=True)

        return newRoot

    @classmethod
    @decorator.check_comp_condition
    def get_componentGuide(cls, componentType):
        """
        Get component guide name in the scene.

        Args:
            name (str):

        Returns:
            pynode: guide name.
        """
        return mgear.shifter.guide.Rig().getComponentGuide(componentType)

    def duplicate_guide(self, nodes, symmetrize=False):
        for i_node in nodes:
            pm.select(i_node, r=True)
            node = self.get_root_from_selection()

            if node:
                mgear.shifter.guide.Rig().duplicate(pm.PyNode(node),
                                                    symmetrize)
            else:
                pm.warning("Can not got guide root.")
