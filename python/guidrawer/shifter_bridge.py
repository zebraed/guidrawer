"""Module that centralizes integration with the mGear (shifter) API.

When mGear implementation changes, impact should stay confined to this
module. Other guidrawer modules must not import mGear directly.
"""
import os
from contextlib import contextmanager

from maya import cmds
import mgear.pymaya as pm
import mgear.shifter
from mgear.shifter import guide as shifter_guide
from mgear.shifter.component import chain_guide_initializer

from . import exception

# Cache chain-type detection per comp_type
_chain_type_cache = {}


def list_component_types():
    """Return all component type names recognized by mGear.

    Includes classic, EPIC, and custom components from
    MGEAR_SHIFTER_COMPONENT_PATH.

    Returns:
        list[str]: Sorted list of component type names.
    """
    names = set()
    for path, entries in mgear.shifter.getComponentDirectories().items():
        for entry in entries:
            # Only directories with __init__.py are valid components
            if os.path.exists(os.path.join(path, entry, "__init__.py")):
                names.add(entry)
    return sorted(names)


def get_component_guide(comp_type):
    """Return the Guide instance for a component.

    Args:
        comp_type (str): Component type name.

    Returns:
        ComponentGuide: mGear guide instance.
    """
    return shifter_guide.Rig().getComponentGuide(comp_type)


def get_default_name(comp_type):
    """Return the default component name defined by mGear (NAME)."""
    return get_component_guide(comp_type).compName


def get_next_component_index(name, side, comp_type, parent, start_index=0):
    """Return a valid component index using mGear ComponentGuide.setIndex().

    Mirrors draw() / rename() in mgear.shifter.component.guide.ComponentGuide.
    """
    comp_guide = get_component_guide(comp_type)
    comp_guide.root = None
    comp_guide.setParamDefValue("comp_name", name)
    comp_guide.setParamDefValue("comp_side", side)
    comp_guide.setParamDefValue("comp_index", start_index)

    parent_node = _get_index_parent_node(parent)
    if not parent_node:
        return start_index

    # Same call as ComponentGuide.draw(): self.setIndex(self.parent)
    comp_guide.setIndex(parent_node)
    return comp_guide.values["comp_index"]


def _get_index_parent_node(parent):
    """Return the draw parent passed to Rig.drawNewComponent()."""
    if parent:
        validated = validate_guide(parent)
        if validated:
            return pm.PyNode(validated)
    return None


def is_chain_type(comp_type):
    """Return whether the component is chain-like (needs section count).

    Uses the same rule as mGear: any name in save_transform containing "#".
    """
    if comp_type not in _chain_type_cache:
        # Custom components may fail to import
        try:
            comp_guide = get_component_guide(comp_type)
        except Exception:
            cmds.warning(f"Can not load component guide. : {comp_type}")
            _chain_type_cache[comp_type] = False
            return False
        has_multi_loc = any("#" in name for name in comp_guide.save_transform)
        _chain_type_cache[comp_type] = has_multi_loc
    return _chain_type_cache[comp_type]


class _ChainDialogStub:
    """Stub that mimics the chain_guide_initializer dialog result."""

    def __init__(self, sections_number, dir_axis, spacing):
        self.sections_number = sections_number
        self.dir_axis = dir_axis
        self.spacing = spacing


@contextmanager
def _override_chain_dialog(sections_number, dir_axis, spacing):
    """Inject chain init values without showing the modal dialog.

    Position calculation still goes through mGear's modalPositions(), so
    changes to mGear's logic are picked up automatically.
    """
    stub = _ChainDialogStub(sections_number, dir_axis, spacing)
    original = chain_guide_initializer.exec_window
    chain_guide_initializer.exec_window = lambda *args: stub
    try:
        yield
    finally:
        chain_guide_initializer.exec_window = original


def validate_guide(root):
    """Return root if it is a valid Shifter guide element, else None.

    Args:
        root (str): Node name to validate.

    Returns:
        str or None: Valid guide element node name.
    """
    if cmds.objExists(f"{root}.isGearGuide"):
        if cmds.getAttr(f"{root}.isGearGuide"):
            return root
        cmds.warning(f"{root} is guide. but not check on .isGearGuide")
        return None
    if cmds.objExists(f"{root}.ismodel"):
        return root
    cmds.warning(f"{root} is not a Shifter guide element.")
    return None


def get_component_root(node):
    """Walk up from node and return the component root with comp_type.

    Args:
        node (str): Starting node name.

    Returns:
        str or None: Component root node name.
    """
    full_paths = cmds.ls(node, l=True)
    if not full_paths:
        return None

    parts = full_paths[0].split("|")
    while parts:
        candidate = "|".join(parts)
        if candidate and cmds.objExists(f"{candidate}.comp_type"):
            return candidate
        parts.pop()
    return None


def draw_component(parent, comp_type, chain_opt=None):
    """Draw a component guide using mGear's standard flow.

    Parameter inheritance from parent (side, ui_host, ctlGrp, etc.) is
    handled by mGear's Rig.drawNewComponent().

    Args:
        parent (str): Parent guide node name.
        comp_type (str): Component type name.
        chain_opt (dict, optional): Options for chain components with keys
            sections_number, dir_axis, spacing. If omitted, mGear's default
            dialog is shown.

    Returns:
        str or None: New guide root name.
    """
    if not cmds.objExists(parent):
        raise exception.NotExistError(
            f"Parent object is not exists. : {parent}"
        )

    rig = shifter_guide.Rig()
    parent_node = pm.PyNode(parent)
    if chain_opt:
        with _override_chain_dialog(**chain_opt):
            result = rig.drawNewComponent(parent_node, comp_type, showUI=False)
    else:
        result = rig.drawNewComponent(parent_node, comp_type, showUI=False)

    if not result:
        return None

    # After draw, the new root is selected
    return cmds.ls(sl=True)[0]


def rename_component(root, name, side, idx):
    """Rename a component guide.

    Args:
        root (str): Guide root node name.
        name (str): New component name.
        side (str): Side (C / L / R).
        idx (int): Component index.

    Returns:
        str: Guide root name after rename.
    """
    root_node = pm.PyNode(root)
    comp_type = root_node.attr("comp_type").get()
    comp_guide = get_component_guide(comp_type)
    comp_guide.rename(root_node, name, side, idx)
    return root_node.name()


def duplicate_component(root, symmetrize=False):
    """Duplicate a component guide.

    Args:
        root (str): Component root node name.
        symmetrize (bool): If True, duplicate symmetrically on the X axis.
    """
    shifter_guide.Rig().duplicate(pm.PyNode(root), symmetrize)
