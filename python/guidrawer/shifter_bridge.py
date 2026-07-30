"""Module that centralizes integration with the mGear (shifter) API.

When mGear implementation changes, impact should stay confined to this
module. Other guidrawer modules must not import mGear directly.
"""
import os
from contextlib import contextmanager

from maya import cmds
import mgear
from mgear.compatible import compatible_comp_dagmenu
from mgear.core import dag
from mgear.core import pyqt
from mgear.vendor.Qt import QtCore
import mgear.pymaya as pm
import mgear.shifter as shifter
from mgear.shifter import guide as shifter_guide
from mgear.shifter import guide_manager
from mgear.shifter import utils as shifter_utils
from mgear.shifter.component import chain_guide_initializer
from mgear.shifter.guide_explorer import utils as guide_explorer_utils
from mgear.shifter.guide_tools import chain_utils
from mgear.shifter.guide_tools import component_type_lister
from mgear.shifter.guide_tools import guide_symmetry_tool
import mgear.rigbits as rigbits
from mgear.rigbits import mirror_controls

from . import exception

# Cache chain-type detection per comp_type
_chain_type_cache = {}

# In-memory pre-settings values (template guides are not kept in the scene)
_pre_settings_cache = {}

_PRE_SETTINGS_TYPE_ATTR = "guidrawerPreSettingsType"
_PRE_SETTINGS_CHAIN_ATTR = "guidrawerPreSettingsChainOpt"
_PRE_SETTINGS_NAME_PREFIX = "_guidrawerPreSettings"
_SKIP_PRE_SETTINGS_PARAMS = {
    "comp_name",
    "comp_side",
    "comp_index",
    "comp_type",
    "comp_local_name",
}

_TEMP_UNPARENT_GROUP = "guidrawer_temp_unparent_grp"
_ORIGINAL_PARENT_ATTR = "guidrawerOriginalParent"


def list_component_types():
    """Return all component type names recognized by mGear.

    Includes classic, EPIC, and custom components from
    MGEAR_SHIFTER_COMPONENT_PATH.

    Returns:
        list[str]: Sorted list of component type names.
    """
    names = set()
    for path, entries in shifter.getComponentDirectories().items():
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
    draw_parent = resolve_draw_parent(parent)
    if draw_parent:
        return pm.PyNode(draw_parent)
    return None


def get_guide_model():
    """Return guide model transform name in the scene, or None."""
    for entry in shifter_utils.get_guide():
        name = _resolve_rig_transform_name(entry)
        if name and cmds.objExists(name):
            if cmds.objExists(f"{name}.ismodel"):
                return name
    return None


def resolve_draw_parent(parent):
    """Resolve parent for drawing a component.

    When parent is empty, use the existing guide model if present.
    Otherwise return None so mGear creates the initial guide hierarchy.
    """
    if parent and str(parent).strip():
        return validate_guide(str(parent).strip())

    return get_guide_model()


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
def _disabled_mgear_log():
    """Temporarily disable mGear stdout logging."""
    previous = mgear.logMode
    mgear.logMode = False
    try:
        yield
    finally:
        mgear.logMode = previous


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


def _is_dag_component(name):
    if not name or "." not in name:
        return False
    return "[" in name.split(".", 1)[1]


def _get_node_world_position(node):
    """Return world position for a transform or DAG component."""
    if not node:
        return None

    if _is_dag_component(node):
        try:
            return cmds.pointPosition(node, w=True)
        except RuntimeError:
            return None

    if not cmds.objExists(node):
        return None

    node_type = cmds.nodeType(node)
    if node_type in ("mesh", "nurbsCurve", "nurbsSurface"):
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        if parents:
            node = parents[0]
        else:
            return None

    return cmds.xform(node, q=True, ws=True, t=True)


def get_node_world_x(node):
    """Return world-space X translation of a node or component."""
    position = _get_node_world_position(node)
    if not position:
        return 0.0
    return position[0]


def side_from_world_x(x, tolerance=1e-6):
    """Return mGear side label from world-space X position."""
    if abs(x) <= tolerance:
        return "C"
    if x > 0.0:
        return "L"
    return "R"


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


def collect_component_placement_locs(comp_root):
    """Return placement locator paths for a component guide root.

    Chain components return all chain placement locators. Other components
    return the primary root locator only.
    """
    full_paths = cmds.ls(comp_root, l=True)
    if not full_paths:
        return []

    comp_root = full_paths[0]
    if not cmds.objExists(f"{comp_root}.comp_type"):
        return [comp_root]

    comp_type = cmds.getAttr(f"{comp_root}.comp_type")
    comp_guide = get_component_guide(comp_type)
    comp_guide.setFromHierarchy(pm.PyNode(comp_root))
    if not comp_guide.valid or not comp_guide.guide_locators:
        return [comp_root]

    locs = []
    for loc_name in comp_guide.guide_locators:
        node = dag.findChild(comp_guide.model, loc_name)
        if node:
            locs.append(node.longName())

    if not locs:
        return [comp_root]
    if is_chain_type(comp_type):
        return locs
    return [locs[0]]


def get_draw_parent_from_selection(node):
    """Return a guide node to parent under when UI parent is empty.

    Args:
        node (str): Selected node name.

    Returns:
        str or None: Valid guide element to use as draw parent.
    """
    if not node or not cmds.objExists(node):
        return None

    guide_root = validate_guide(node)
    if guide_root:
        return guide_root

    component_root = get_component_root(node)
    if component_root:
        return validate_guide(component_root)
    return None


def get_settings_root(node):
    """Return component root or guide model for opening settings UI.

    Walks up from the given node, matching mGear inspect_settings behavior.
    """
    if not node or not cmds.objExists(node):
        return None

    current = node
    visited = set()
    while current and current not in visited:
        visited.add(current)
        if cmds.objExists(f"{current}.comp_type"):
            return current
        if cmds.objExists(f"{current}.ismodel"):
            return current
        parents = cmds.listRelatives(current, parent=True, fullPath=True)
        if not parents:
            break
        current = parents[0]
    return None


def get_parent_component_root(node):
    """Return the component root directly above node, or None."""
    full_paths = cmds.ls(node, l=True)
    if not full_paths:
        return None

    parts = full_paths[0].split("|")
    if len(parts) <= 1:
        return None

    parts.pop()
    while parts:
        candidate = "|".join(parts)
        if candidate and cmds.objExists(f"{candidate}.comp_type"):
            return candidate
        parts.pop()
    return None


def list_child_component_roots(root):
    """Return nested component roots whose parent component is root."""
    root_paths = cmds.ls(root, l=True)
    if not root_paths:
        return []

    root_path = root_paths[0]
    child_roots = []
    descendants = cmds.listRelatives(
        root,
        allDescendents=True,
        fullPath=True,
        type="transform",
    )
    if not descendants:
        return child_roots

    for node in descendants:
        if not cmds.attributeQuery("comp_type", node=node, exists=True):
            continue
        if get_parent_component_root(node) == root_path:
            child_roots.append(node)
    return child_roots


def set_guide_to_parent_origin(guide_root):
    """Place guide_root at the origin of its current parent space."""
    if guide_root and cmds.objExists(guide_root):
        cmds.xform(guide_root, os=True, t=(0, 0, 0))


def draw_component(parent, comp_type, chain_opt=None):
    """Draw a component guide using mGear's standard flow.

    Parameter inheritance from parent (side, ui_host, ctlGrp, etc.) is
    handled by mGear's Rig.drawNewComponent().

    Args:
        parent (str or None): Parent guide node name. None creates the
            initial guide hierarchy when no guide exists in the scene.
        comp_type (str): Component type name.
        chain_opt (dict, optional): Options for chain components with keys
            sections_number, dir_axis, spacing. If omitted, mGear's default
            dialog is shown.

    Returns:
        str or None: New guide root name.
    """
    parent_node = None
    if parent:
        if not cmds.objExists(parent):
            raise exception.NotExistError(
                f"Parent object is not exists. : {parent}"
            )
        parent_node = pm.PyNode(parent)

    rig = shifter_guide.Rig()
    if chain_opt:
        with _override_chain_dialog(**chain_opt):
            result = rig.drawNewComponent(
                parent_node, comp_type, showUI=False
            )
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


def delete_component(root):
    """Delete a component guide.

    Same as mGear Guide Explorer's Delete: delete the component root node
    (child components under it are also removed).

    Args:
        root (str): Component root node name.
    """
    pm.delete(pm.PyNode(root))


def delete_component_keep_children(root):
    """Delete a component guide and reparent nested components to its parent.

    Args:
        root (str): Component root node name.
    """
    parents = cmds.listRelatives(root, parent=True, fullPath=True)
    new_parent = parents[0] if parents else None

    for child_root in list_child_component_roots(root):
        if new_parent:
            cmds.parent(child_root, new_parent)
        else:
            cmds.parent(child_root, world=True)

    delete_component(root)


def _get_temp_unparent_group(create=False):
    """Return the world-level temporary unparent group."""
    group_path = f"|{_TEMP_UNPARENT_GROUP}"
    if cmds.objExists(group_path):
        if cmds.nodeType(group_path) != "transform":
            cmds.warning(
                f"{_TEMP_UNPARENT_GROUP} exists and is not a transform."
            )
            return None
        return pm.PyNode(group_path)

    if not create:
        return None
    return pm.group(empty=True, world=True, name=_TEMP_UNPARENT_GROUP)


def list_temporary_unparented_components():
    """Return component roots under the temporary unparent group."""
    temp_group = _get_temp_unparent_group()
    if temp_group is None:
        return []

    children = temp_group.getChildren(type="transform")
    if not children:
        return []

    roots = []
    for child in children:
        if child.hasAttr(_ORIGINAL_PARENT_ATTR):
            roots.append(child.longName())
    return roots


def has_temporary_unparented_components():
    """Return whether any component is temporarily unparented."""
    return bool(list_temporary_unparented_components())


def parent_components(roots, parent=None):
    """Parent component roots under parent, or world if parent is None.

    World transform is preserved.

    Args:
        roots: Component root names or PyNodes.
        parent: Destination parent transform, or None for world.

    Returns:
        list: Parented PyNode roots.
    """
    if not roots:
        return []

    moved = []
    for root in roots:
        node = pm.PyNode(root)
        if parent is None:
            pm.parent(node, world=True, absolute=True)
        else:
            pm.parent(node, parent, absolute=True)
        moved.append(node)
    return moved


def temporary_unparent_components(roots):
    """Parent component roots under a temporary world-level group."""
    if not roots:
        return

    root_nodes = [pm.PyNode(root) for root in roots]
    temp_group = _get_temp_unparent_group(create=True)
    if temp_group is None:
        return

    to_move = []
    for root in root_nodes:
        if root.hasAttr(_ORIGINAL_PARENT_ATTR):
            cmds.warning(f"{root.name()}: Is already temporarily unparented.")
            continue

        root.addAttr(_ORIGINAL_PARENT_ATTR, attributeType="message")
        original_parent = root.getParent()
        if original_parent is not None:
            original_parent.message.connect(
                root.attr(_ORIGINAL_PARENT_ATTR)
            )
        to_move.append(root)

    moved = parent_components(to_move, temp_group)
    if moved:
        pm.select(moved, r=True)


def reparent_components(roots):
    """Restore temporarily unparented component roots."""
    if not roots:
        return

    root_nodes = [pm.PyNode(root) for root in roots]
    restored = []
    for root in root_nodes:
        if not root.hasAttr(_ORIGINAL_PARENT_ATTR):
            cmds.warning(f"{root.name()}: Is not temporarily unparented.")
            continue

        original_parents = root.attr(
            _ORIGINAL_PARENT_ATTR
        ).listConnections(s=True, d=False)
        parent = original_parents[0] if original_parents else None
        restored.extend(parent_components([root], parent))
        pm.deleteAttr(root.attr(_ORIGINAL_PARENT_ATTR))

    temp_group = _get_temp_unparent_group()
    if temp_group is not None and not temp_group.getChildren():
        pm.delete(temp_group)

    if restored:
        pm.select(restored, r=True)


def _get_pre_settings_component_name(comp_type):
    safe_type = comp_type.replace("-", "_").replace(".", "_")
    return f"{_PRE_SETTINGS_NAME_PREFIX}_{safe_type}"


def _chain_opt_from_signature(signature):
    if not signature:
        return None
    parts = signature.split(":")
    if len(parts) != 3:
        return None
    return {
        "sections_number": int(parts[0]),
        "dir_axis": int(parts[1]),
        "spacing": float(parts[2]),
    }


def _prompt_chain_opt():
    """Show mGear's Chain Initializer dialog and return its values."""
    init_window = chain_guide_initializer.exec_window()
    if not init_window:
        return None
    return {
        "sections_number": init_window.sections_number,
        "dir_axis": init_window.dir_axis,
        "spacing": init_window.spacing,
    }


def _resolve_chain_opt_for_pre_settings(comp_type):
    """Return chain draw options from cache or the Chain Initializer dialog."""
    if not is_chain_type(comp_type):
        return None

    entry = _pre_settings_cache.get(comp_type)
    if entry and entry.get("chain_opt"):
        return entry["chain_opt"]

    return _prompt_chain_opt()


def get_pre_settings_chain_opt(comp_type):
    """Return cached chain draw options for comp_type, if any."""
    entry = _pre_settings_cache.get(comp_type)
    if not entry:
        return None
    return entry.get("chain_opt")


def has_component_settings(comp_type):
    """Return whether comp_type exposes mGear's componentSettings UI."""
    try:
        module = shifter.importComponentGuide(comp_type)
    except Exception:
        return False
    return getattr(module, "componentSettings", None) is not None


def _get_chain_opt_signature(chain_opt):
    if not chain_opt:
        return ""
    sections = chain_opt.get("sections_number", "")
    axis = chain_opt.get("dir_axis", "")
    spacing = chain_opt.get("spacing", "")
    return f"{sections}:{axis}:{spacing}"


def _pre_settings_cache_key(comp_type):
    return comp_type


def _get_pre_settings_entry(comp_type):
    return _pre_settings_cache.get(_pre_settings_cache_key(comp_type))


def _list_pre_settings_templates(comp_type=None):
    templates = []
    for node in cmds.ls(type="transform"):
        if not cmds.attributeQuery(
            _PRE_SETTINGS_TYPE_ATTR, node=node, exists=True
        ):
            continue
        if comp_type and cmds.getAttr(
            f"{node}.{_PRE_SETTINGS_TYPE_ATTR}"
        ) != comp_type:
            continue
        if cmds.objExists(f"{node}.comp_type"):
            templates.append(node)
    return templates


def _read_component_param_values(comp_type, root):
    """Read component parameter values from root into a serializable dict."""
    comp_guide = get_component_guide(comp_type)
    values = {}
    for script_name in comp_guide.paramNames:
        if script_name in _SKIP_PRE_SETTINGS_PARAMS:
            continue
        source_plug = f"{root}.{script_name}"
        if not cmds.objExists(source_plug):
            continue
        param_def = comp_guide.paramDefs[script_name]
        if param_def.__class__.__name__ == "FCurveParamDef":
            continue

        source_connections = cmds.listConnections(
            source_plug, source=True, destination=False, plugs=True
        )
        if source_connections:
            values[script_name] = ("connection", source_connections[0])
            continue

        attr_type = cmds.getAttr(source_plug, type=True)
        if attr_type == "string":
            values[script_name] = ("string", cmds.getAttr(source_plug))
        elif attr_type in ("double3", "float3"):
            values[script_name] = ("double3", cmds.getAttr(source_plug)[0])
        else:
            values[script_name] = ("scalar", cmds.getAttr(source_plug))
    return values


def _apply_cached_param_value(target_plug, payload):
    kind, value = payload
    target_connections = cmds.listConnections(
        target_plug, source=True, destination=False, plugs=True
    )
    if kind == "connection":
        if target_connections:
            cmds.disconnectAttr(target_connections[0], target_plug)
        cmds.connectAttr(value, target_plug, force=True)
        return

    if target_connections:
        cmds.disconnectAttr(target_connections[0], target_plug)

    if kind == "string":
        cmds.setAttr(target_plug, value, type="string")
    elif kind == "double3":
        cmds.setAttr(target_plug, *value)
    else:
        cmds.setAttr(target_plug, value)


def _apply_component_param_values(comp_type, target_root, values):
    """Apply cached parameter values onto target_root."""
    comp_guide = get_component_guide(comp_type)
    for script_name in comp_guide.paramNames:
        if script_name in _SKIP_PRE_SETTINGS_PARAMS:
            continue
        if script_name not in values:
            continue
        target_plug = f"{target_root}.{script_name}"
        if not cmds.objExists(target_plug):
            continue
        _apply_cached_param_value(target_plug, values[script_name])


def _store_pre_settings_cache(comp_type, root, chain_opt=None):
    cache_key = _pre_settings_cache_key(comp_type)
    entry = _pre_settings_cache.get(cache_key)
    if chain_opt is None and entry:
        chain_opt = entry.get("chain_opt")
    _pre_settings_cache[cache_key] = {
        "values": _read_component_param_values(comp_type, root),
        "chain_opt": chain_opt,
    }


def cleanup_pre_settings_templates():
    """Remove leftover pre-settings templates and keep their values in memory."""
    for node in _list_pre_settings_templates():
        comp_type = cmds.getAttr(f"{node}.{_PRE_SETTINGS_TYPE_ATTR}")
        chain_opt = None
        if cmds.attributeQuery(
            _PRE_SETTINGS_CHAIN_ATTR, node=node, exists=True
        ):
            signature = cmds.getAttr(f"{node}.{_PRE_SETTINGS_CHAIN_ATTR}")
            if signature is None:
                signature = ""
            chain_opt = _chain_opt_from_signature(signature)
        _store_pre_settings_cache(comp_type, node, chain_opt)
        _delete_pre_settings_template(node)


def _mark_pre_settings_template(root, comp_type, chain_signature):
    for attr_name, value in (
        (_PRE_SETTINGS_TYPE_ATTR, comp_type),
        (_PRE_SETTINGS_CHAIN_ATTR, chain_signature),
    ):
        if not cmds.attributeQuery(attr_name, node=root, exists=True):
            cmds.addAttr(root, longName=attr_name, dataType="string")
        cmds.setAttr(f"{root}.{attr_name}", value, type="string")


def find_pre_settings_template(comp_type):
    """Return a hidden pre-settings template root for comp_type, if any."""
    for node in _list_pre_settings_templates(comp_type):
        return node
    return None


def _delete_pre_settings_template(root):
    if root and cmds.objExists(root):
        delete_component(root)


def copy_component_param_values(comp_type, source_root, target_root):
    """Copy component parameter values from source_root to target_root."""
    values = _read_component_param_values(comp_type, source_root)
    _apply_component_param_values(comp_type, target_root, values)


def create_pre_settings_template(comp_type, parent, chain_opt=None):
    """Create a temporary hidden template guide for pre-settings editing."""
    parent = validate_guide(parent)
    if not parent:
        return None

    chain_signature = _get_chain_opt_signature(chain_opt)
    for node in _list_pre_settings_templates(comp_type):
        _delete_pre_settings_template(node)

    try:
        cmds.undoInfo(openChunk=True)
        guide_root = draw_component(parent, comp_type, chain_opt)
        if not guide_root:
            return None

        template_name = _get_pre_settings_component_name(comp_type)
        guide_root = rename_component(guide_root, template_name, "C", 0)
        _mark_pre_settings_template(guide_root, comp_type, chain_signature)
        cmds.setAttr(f"{guide_root}.visibility", 0)
        return guide_root
    finally:
        cmds.undoInfo(closeChunk=True)


def get_or_create_pre_settings_template(comp_type, parent, chain_opt=None):
    """Backward-compatible alias for create_pre_settings_template."""
    return create_pre_settings_template(comp_type, parent, chain_opt)


class _PreSettingsDialogWatcher(QtCore.QObject):
    """Finalize the pre-settings template when the dialog is closed.
    """

    def __init__(self, dialog, finalize):
        super().__init__(dialog)
        self.__dialog = dialog
        self.__finalize = finalize
        dialog.installEventFilter(self)
        dialog.destroyed.connect(finalize)

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Close, QtCore.QEvent.Hide):
            QtCore.QTimer.singleShot(0, self.__check_closed)
        return False

    def __check_closed(self):
        try:
            visible = self.__dialog.isVisible()
        except RuntimeError:
            visible = False
        if not visible:
            self.__finalize()


def open_pre_settings(comp_type, parent):
    """Open mGear component settings on a temporary pre-settings template."""
    if not has_component_settings(comp_type):
        cmds.warning("This component type has no settings UI.")
        return None

    chain_opt = _resolve_chain_opt_for_pre_settings(comp_type)
    if is_chain_type(comp_type) and chain_opt is None:
        return None

    template = create_pre_settings_template(comp_type, parent, chain_opt)
    if not template:
        return None

    entry = _get_pre_settings_entry(comp_type)
    if entry and entry.get("values"):
        _apply_component_param_values(
            comp_type, template, entry["values"]
        )

    cmds.select(template, r=True)
    guide_module = shifter.importComponentGuide(comp_type)

    dialog = pyqt.showDialog(
        guide_module.componentSettings, dockable=True
    )

    def _finalize_pre_settings_template():
        if not cmds.objExists(template):
            return
        if not cmds.attributeQuery(
            _PRE_SETTINGS_TYPE_ATTR, node=template, exists=True
        ):
            return
        _store_pre_settings_cache(comp_type, template, chain_opt)
        _delete_pre_settings_template(template)

    if dialog:
        _PreSettingsDialogWatcher(dialog, _finalize_pre_settings_template)
    return template


def has_pre_settings_cache(comp_type):
    """Return whether cached pre-settings exist for comp_type."""
    entry = _get_pre_settings_entry(comp_type)
    if entry and entry.get("values"):
        return True
    if find_pre_settings_template(comp_type):
        return True
    return False


def reset_pre_settings(comp_type):
    """Discard cached pre-settings and remove any leftover template guides."""
    cache_key = _pre_settings_cache_key(comp_type)
    had_cache = cache_key in _pre_settings_cache
    if had_cache:
        del _pre_settings_cache[cache_key]

    templates = _list_pre_settings_templates(comp_type)
    for node in templates:
        _delete_pre_settings_template(node)

    return had_cache or bool(templates)


def apply_pre_settings(comp_type, target_root):
    """Apply pre-settings from memory cache to a newly created guide."""
    if not target_root or not cmds.objExists(target_root):
        return False

    entry = _get_pre_settings_entry(comp_type)
    if entry and entry.get("values"):
        _apply_component_param_values(
            comp_type, target_root, entry["values"]
        )
        return True

    template = find_pre_settings_template(comp_type)
    if not template:
        return False

    copy_component_param_values(comp_type, template, target_root)
    return True


def open_settings_from_selection(nodes):
    """Open mGear settings for the current selection.

    When nothing is selected, opens Guide Top settings on the guide model.
    """
    if not nodes:
        if cmds.objExists("guide"):
            guide = pm.PyNode("guide")
            if guide.hasAttr("ismodel"):
                open_component_settings("guide")
                return
        cmds.warning("Nothing selected.")
        return

    for node in nodes:
        settings_root = get_settings_root(node)
        if settings_root:
            open_component_settings(settings_root)
            return
    cmds.warning("The selected object is not part of component guide.")


def open_component_settings(root):
    """Open mGear component or guide root settings UI.

    Uses mGear guide_manager.inspect_settings, which resolves the
    target from the current selection.

    Args:
        root (str): Component root or guide model node name.
    """
    settings_root = get_settings_root(root)
    if not settings_root:
        cmds.warning("The selected object is not part of component guide.")
        return

    cmds.select(settings_root, r=True)
    guide_manager.inspect_settings()


_CURVE_SHAPE_TYPES = ("nurbsCurve", "bezierCurve")


def _has_curve_shape(node):
    shapes = cmds.listRelatives(
        node,
        shapes=True,
        fullPath=True,
        noIntermediate=True,
    )
    if not shapes:
        return False
    for shape in shapes:
        if cmds.nodeType(shape) in _CURVE_SHAPE_TYPES:
            return True
    return False


def _is_rig_root_node(node):
    if not node or not cmds.objExists(node):
        return False
    if cmds.attributeQuery("is_rig", node=node, exists=True):
        return bool(cmds.getAttr(f"{node}.is_rig"))
    return False


def _list_rig_control_nodes(rig_root):
    """Return mGear controls under rig_root that have curve shapes."""
    if not rig_root or not cmds.objExists(rig_root):
        return []

    descendants = cmds.listRelatives(
        rig_root,
        allDescendents=True,
        type="transform",
        fullPath=True,
    )
    if not descendants:
        return []

    controls = []
    for node in descendants:
        if node.rsplit("|", 1)[-1].endswith("_controlBuffer"):
            continue
        if not cmds.attributeQuery("isCtl", node=node, exists=True):
            continue
        if _has_curve_shape(node):
            controls.append(node)
    return controls


def _collect_extract_targets(selection):
    """Build extract targets, expanding rig root to all controller shapes."""
    targets = []
    seen = set()

    if not selection:
        for rig_root in _list_built_rig_transforms():
            for control in _list_rig_control_nodes(rig_root):
                if control not in seen:
                    targets.append(control)
                    seen.add(control)
        return targets

    for node in selection:
        if _is_rig_root_node(node):
            for control in _list_rig_control_nodes(node):
                if control not in seen:
                    targets.append(control)
                    seen.add(control)
            continue
        if node not in seen:
            targets.append(node)
            seen.add(node)
    return targets


def _is_extractable_control(node):
    if not cmds.objExists(node):
        return False
    return cmds.attributeQuery("isCtl", node=node, exists=True)


def _get_extract_selection(selection):
    """Return selection for Extr. Ctrl, selecting parent transforms for shapes.

    Extr. Ctrl requires transforms with isCtl. When only shapes are selected
    (e.g. after Sel Shape), switch selection to their parent transforms.
    """
    if not selection:
        return selection

    transforms = []
    seen = set()
    has_shape = False
    for node in selection:
        base = node.split(".", 1)[0]
        if cmds.objExists(base) and cmds.objectType(base, isAType="shape"):
            has_shape = True
            parents = cmds.listRelatives(base, parent=True, fullPath=True)
            if not parents:
                continue
            transform = parents[0]
        else:
            transform = node

        if transform not in seen:
            transforms.append(transform)
            seen.add(transform)

    if has_shape and transforms:
        cmds.select(transforms, r=True)
        return transforms
    return selection


def _extract_shape_to_buffer(node, controllers_org):
    """Extract one control or guide shape into controllers_org."""
    control = pm.PyNode(node)
    short_name = control.name().split("|")[-1]
    buffer_name = f"{short_name}_controlBuffer"
    try:
        old = pm.PyNode(f"{controllers_org.name()}|{buffer_name}")
        pm.delete(old)
    except (TypeError, RuntimeError):
        pass

    new = pm.duplicate(control)[0]
    pm.parent(new, controllers_org, a=True)
    pm.rename(new, buffer_name)
    to_delete = new.getChildren(type="transform", fullPath=True)
    if to_delete:
        pm.delete(to_delete)
    try:
        for obj_set in control.instObjGroups[0].listConnections(type="objectSet"):
            pm.sets(obj_set, remove=new)
    except TypeError:
        pass


def extract_controls():
    """Extract selected controls to controllers_org buffers.

    When nothing is selected or the rig root is selected, all controller
    shapes under the built rig are extracted.
    Shape selection is converted to parent transforms before extract.
    """
    selection = _get_extract_selection(cmds.ls(sl=True, long=True))

    try:
        controllers_org = pm.PyNode("controllers_org")
    except (TypeError, RuntimeError):
        cmds.warning(
            "No controllers_org group in the scene or the group is not unique."
        )
        return

    targets = _collect_extract_targets(selection)
    if not targets:
        if not selection:
            cmds.warning("No built rig found in the scene.")
        else:
            cmds.warning("No controller shapes found to extract.")
        return

    extracted = 0
    for node in targets:
        if not _is_extractable_control(node):
            cmds.warning(f"{node}: Is not a valid mGear control.")
            continue
        _extract_shape_to_buffer(node, controllers_org)
        extracted += 1

    if extracted:
        cmds.select(targets, r=True)
    else:
        cmds.warning("No controls were extracted.")


def _parse_custom_step_scripts(step_value):
    """Return active custom step paths using mGear's parser."""
    text = str(step_value).strip() if step_value else ""
    if not text:
        return []
    return shifter.Rig()._parseCustomSteps(text)


def _has_custom_step_scripts(step_value):
    return len(_parse_custom_step_scripts(step_value)) > 0


def _get_custom_step_strings_from_guide(guide):
    """Return pre/post custom step strings effective for the guide.
    """
    pre = ""
    post = ""
    if guide.hasAttr("preCustomStep"):
        pre = guide.attr("preCustomStep").get() or ""
    if guide.hasAttr("postCustomStep"):
        post = guide.attr("postCustomStep").get() or ""

    use_blueprint = (
        guide.hasAttr("use_blueprint")
        and guide.attr("use_blueprint").get()
        and guide.hasAttr("blueprint_path")
    )
    if not use_blueprint:
        return pre, post

    blueprint_path = guide.attr("blueprint_path").get()
    if not blueprint_path:
        return pre, post

    blueprint_conf = shifter_guide.load_blueprint_guide(blueprint_path)
    if not blueprint_conf:
        return pre, post

    param_values = blueprint_conf.get("guide_root", {}).get("param_values", {})
    if not param_values:
        return pre, post

    override_pre = (
        guide.hasAttr("override_pre_custom_steps")
        and guide.attr("override_pre_custom_steps").get()
    )
    override_post = (
        guide.hasAttr("override_post_custom_steps")
        and guide.attr("override_post_custom_steps").get()
    )

    if not override_pre:
        pre = param_values.get("preCustomStep", pre) or ""
    if not override_post:
        post = param_values.get("postCustomStep", post) or ""

    return pre, post


def has_full_build_steps():
    """Return whether guide has pre or post custom scripts configured."""
    if not cmds.objExists("guide"):
        return False

    guide = pm.PyNode("guide")
    if not guide.hasAttr("ismodel"):
        return False
    if not guide.hasAttr("preCustomStep") and not guide.hasAttr("postCustomStep"):
        return False

    pre_steps, post_steps = _get_custom_step_strings_from_guide(guide)
    return (
        _has_custom_step_scripts(pre_steps)
        or _has_custom_step_scripts(post_steps)
    )


def update_component_type():
    """Open mGear Update Component Type UI for the current selection."""
    compatible_comp_dagmenu.update_component_type_and_update_guide_with_dagmenu()


def get_mgear_icon_path(icon_name):
    """Return absolute path to an mGear icon file, or None."""
    path = guide_explorer_utils.get_mgear_icon_path(icon_name)
    if path:
        return str(path)
    return None


def open_guide_symmetry_tool():
    """Open mGear Guide Symmetry Tool."""
    guide_symmetry_tool.open_shifter_mirror_checker()


def open_component_type_lister():
    """Open mGear Component Type Lister."""
    component_type_lister.show()


def open_chain_utils():
    """Open mGear Chain Utils."""
    chain_utils.open_chain_utils()


def _resolve_rig_transform_name(rig_entry):
    """Return rig transform name from a get_rig() entry (node or attribute plug)."""
    if hasattr(rig_entry, "node"):
        return rig_entry.node().name()

    name = rig_entry.name() if hasattr(rig_entry, "name") else str(rig_entry)
    if "." in name:
        return name.split(".", 1)[0]
    return name


def _list_built_rig_transforms():
    """Return transform node names for built mGear rigs in the scene."""
    transforms = []
    seen = set()
    for rig_entry in shifter_utils.get_rig():
        rig_name = _resolve_rig_transform_name(rig_entry)
        if rig_name and rig_name not in seen and cmds.objExists(rig_name):
            seen.add(rig_name)
            transforms.append(rig_name)
    return transforms


def has_built_rig():
    """Return whether the scene contains a built mGear rig."""
    return bool(_list_built_rig_transforms())


def unbuild_guide():
    """Unbuild the current rig in the scene, same as Guide Explorer Unbuild."""
    rig_transforms = _list_built_rig_transforms()
    if not rig_transforms:
        cmds.warning("No valid rig has been found in the scene to unbuild.")
        return

    cmds.select(clear=True)
    shifter_utils.delete_nodes(rig_transforms)


def _restore_guide_custom_step_flags(pre_enabled, post_enabled):
    """Restore guide custom step flags when the guide still exists."""
    if not cmds.objExists("guide"):
        return

    guide = pm.PyNode("guide")
    if not guide.hasAttr("doPreCustomStep"):
        return
    if not guide.hasAttr("doPostCustomStep"):
        return

    guide.attr("doPreCustomStep").set(pre_enabled)
    guide.attr("doPostCustomStep").set(post_enabled)


def vanilla_build_guide():
    """Build rig from current selection with pre/post custom steps disabled.

    Matches mGear behavior: builds the selected guide component and its
    children. If nothing is selected, falls back to the ``guide`` model.
    Custom step flags are temporarily disabled, then restored.
    """
    cleanup_pre_settings_templates()

    if not cmds.objExists("guide"):
        cmds.warning("Guide not found.")
        return

    guide = pm.PyNode("guide")
    if not guide.hasAttr("ismodel"):
        cmds.warning("guide is not a valid Shifter guide model.")
        return

    pre_enabled = guide.attr("doPreCustomStep").get()
    post_enabled = guide.attr("doPostCustomStep").get()

    try:
        guide.attr("doPreCustomStep").set(False)
        guide.attr("doPostCustomStep").set(False)
        with _disabled_mgear_log():
            shifter.log_window()
            shifter.Rig().buildFromSelection()
    finally:
        _restore_guide_custom_step_flags(pre_enabled, post_enabled)


def full_build_guide(with_log=False):
    """Build rig from guide with configured pre/post custom steps enabled.

    Args:
        with_log (bool): When True, mGear build log is written to the script editor.
    """
    if not has_full_build_steps():
        cmds.warning("Pre or Post custom scripts are not configured.")
        return

    cleanup_pre_settings_templates()

    if not cmds.objExists("guide"):
        cmds.warning("Guide not found.")
        return

    guide = pm.PyNode("guide")
    if not guide.hasAttr("ismodel"):
        cmds.warning("guide is not a valid Shifter guide model.")
        return

    pre_steps, post_steps = _get_custom_step_strings_from_guide(guide)
    has_pre = _has_custom_step_scripts(pre_steps)
    has_post = _has_custom_step_scripts(post_steps)

    cmds.select("guide", r=True)

    pre_enabled = guide.attr("doPreCustomStep").get()
    post_enabled = guide.attr("doPostCustomStep").get()

    try:
        guide.attr("doPreCustomStep").set(has_pre)
        guide.attr("doPostCustomStep").set(has_post)
        if with_log:
            shifter.log_window()
            shifter.Rig().buildFromSelection()
        else:
            with _disabled_mgear_log():
                shifter.log_window()
                shifter.Rig().buildFromSelection()
    finally:
        _restore_guide_custom_step_flags(pre_enabled, post_enabled)


def replace_control_shape():
    """Run mGear rigbits Replace Shape on the current selection."""
    rigbits.replaceShape()


def mirror_control_shape():
    """Open mGear rigbits Mirror Controls Shape UI."""
    mirror_controls.show()
