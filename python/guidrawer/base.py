from maya import cmds
import mgear.pymaya as pm
import mgear.shifter

from . import decorator
from . import exception


class GuidrawerBase:
    def __init__(self):
        super().__init__()
        self.guide_list = []

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
        if cmds.objExists(f"{root}.isGearGuide"):
            if cmds.getAttr(f"{root}.isGearGuide"):
                root = pm.PyNode(root)
            else:
                cmds.warning(
                    f"{root} is guide. but not check on .isGearGuide"
                )
                return None
        elif cmds.objExists(f"{root}.ismodel"):
            return pm.PyNode(root)

        return root

    @classmethod
    def get_root_from_selection(cls):
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
        selection = cmds.ls(sl=True, l=True)
        if not selection:
            return None

        fp = selection[0].split("|")
        for i in range(len(fp) - 1):
            if i == 0:
                a_l = fp[1:]
            else:
                a_l = fp[1:-i]
            node = "|".join(a_l)
            if "_root" in node:
                if cmds.objExists(f"{node}.comp_type"):
                    return node
        return None

    @classmethod
    def create_temporary_group(cls, parts_name):
        """Create temporary dummy group."""
        return cmds.group(n=f"{parts_name}_tempGp#", em=True)

    @classmethod
    def draw_component(cls, parent, component_type):
        """Draw guide component from string name.

        Args:
            parent (str): parent object.
            component_type (str): draw new component name.
            root (str, optional): target root. Defaults to None.

        Returns:
            str: new guide root name from selection list.

        Example:
            mgear.shifter.guide.Rig().drawNewComponent(
                parent=pm.PyNode("softmodRoot_C0_root"),
                comp_type="control_01",
                showUI=False,
            )
        """
        if parent is not None:
            if cmds.objExists(parent):
                parent = pm.PyNode(parent)
            else:
                raise exception.NotExistError("Parent object is not exists.")

        mgear.shifter.guide.Rig().drawNewComponent(
            parent, component_type, showUI=False
        )
        new_root = cmds.ls(sl=True)[0]
        cmds.select(cl=True)

        return new_root

    @classmethod
    @decorator.check_comp_condition
    def get_componentGuide(cls, component_type):
        """Get component guide name in the scene.

        Args:
            name (str):

        Returns:
            pynode: guide name.
        """
        return mgear.shifter.guide.Rig().getComponentGuide(component_type)

    def duplicate_guide(self, nodes, symmetrize=False):
        for i_node in nodes:
            cmds.select(i_node, r=True)
            node = self.get_root_from_selection()

            if node:
                mgear.shifter.guide.Rig().duplicate(
                    pm.PyNode(node), symmetrize
                )
            else:
                cmds.warning("Can not got guide root.")
