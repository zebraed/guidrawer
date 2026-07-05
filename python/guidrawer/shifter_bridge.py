"""Module that centralizes integration with the mGear (shifter) API.

When mGear implementation changes, impact should stay confined to this
module. Other guidrawer modules must not import mGear directly.
"""
import os
from contextlib import contextmanager

from maya import cmds
import mgear
from mgear.vendor.Qt import QtCore
import mgear.pymaya as pm
import mgear.shifter as shifter
from mgear.shifter import guide as shifter_guide
from mgear.shifter import guide_manager
from mgear.shifter.component import chain_guide_initializer

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
    from mgear.core import pyqt

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


def open_component_settings(root):
    """Open mGear's component/guide settings UI for the given root.

    Uses mGear guide_manager.inspect_settings, which resolves the
    component from the current selection.

    Args:
        root (str): Component root node name.
    """
    cmds.select(root, r=True)
    guide_manager.inspect_settings()


def extract_controls():
    """Extract selected controls to controllers_org buffers.

    Same as mGear menu: Shifter > Extract Controls.
    """
    if not cmds.ls(sl=True):
        cmds.warning("Nothing selected.")
        return

    if not cmds.objExists("controllers_org"):
        cmds.warning(
            "No controllers_org group in the scene or the group is not unique."
        )
        return

    try:
        guide_manager.extract_controls()
    except (TypeError, RuntimeError) as exc:
        cmds.warning(str(exc))


def _has_custom_step_scripts(step_value):
    text = str(step_value).strip()
    if not text:
        return False
    for entry in text.split(","):
        if entry.strip():
            return True
    return False


def has_full_build_steps():
    """Return whether guide has both pre and post custom scripts configured."""
    if not cmds.objExists("guide"):
        return False

    guide = pm.PyNode("guide")
    if not guide.hasAttr("ismodel"):
        return False
    if not guide.hasAttr("preCustomStep") or not guide.hasAttr("postCustomStep"):
        return False

    pre_steps = guide.attr("preCustomStep").get()
    post_steps = guide.attr("postCustomStep").get()
    return (
        _has_custom_step_scripts(pre_steps)
        and _has_custom_step_scripts(post_steps)
    )


def vanilla_build_guide():
    """Build rig from guide with pre/post custom steps disabled.

    Selects ``guide``, temporarily disables custom step flags, builds,
    then restores the original guide settings.
    """
    cleanup_pre_settings_templates()

    if not cmds.objExists("guide"):
        cmds.warning("Guide not found.")
        return

    guide = pm.PyNode("guide")
    if not guide.hasAttr("ismodel"):
        cmds.warning("guide is not a valid Shifter guide model.")
        return

    cmds.select("guide", r=True)

    pre_enabled = guide.attr("doPreCustomStep").get()
    post_enabled = guide.attr("doPostCustomStep").get()

    try:
        guide.attr("doPreCustomStep").set(False)
        guide.attr("doPostCustomStep").set(False)
        with _disabled_mgear_log():
            shifter.log_window()
            shifter.Rig().buildFromSelection()
    finally:
        guide.attr("doPreCustomStep").set(pre_enabled)
        guide.attr("doPostCustomStep").set(post_enabled)


def full_build_guide():
    """Build rig from guide with pre/post custom steps enabled."""
    if not has_full_build_steps():
        cmds.warning("Pre and Post custom scripts are not configured.")
        return

    cleanup_pre_settings_templates()

    if not cmds.objExists("guide"):
        cmds.warning("Guide not found.")
        return

    guide = pm.PyNode("guide")
    if not guide.hasAttr("ismodel"):
        cmds.warning("guide is not a valid Shifter guide model.")
        return

    cmds.select("guide", r=True)

    pre_enabled = guide.attr("doPreCustomStep").get()
    post_enabled = guide.attr("doPostCustomStep").get()

    try:
        guide.attr("doPreCustomStep").set(True)
        guide.attr("doPostCustomStep").set(True)
        shifter.log_window()
        shifter.Rig().buildFromSelection()
    finally:
        guide.attr("doPreCustomStep").set(pre_enabled)
        guide.attr("doPostCustomStep").set(post_enabled)
