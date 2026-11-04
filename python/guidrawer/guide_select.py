"""Selection helpers for guides and rig controls."""
from maya import cmds

from mgear.core import string as mgear_string

from . import shifter_bridge as bridge


_POSITION_TOLERANCE = 0.01
_AXIS_TOLERANCE = 1e-4


def _short_name(node):
    return node.rsplit("|", 1)[-1]


def _get_selection():
    selection = cmds.ls(sl=True, long=True, transforms=True)
    if not selection:
        cmds.warning("Nothing selected.")
    return selection


def _apply_selection(nodes, add):
    """Select nodes. add=True keeps the current selection."""
    nodes = list(dict.fromkeys(nodes))
    if not nodes:
        return
    cmds.select(nodes, add=add, replace=not add)


def _report(found, missing, label):
    if missing:
        cmds.warning(
            f"{label}: no opposite found for {len(missing)} node(s): "
            + ", ".join(_short_name(n) for n in missing[:5])
            + (" ..." if len(missing) > 5 else "")
        )
    if not found and not missing:
        cmds.warning(f"{label}: nothing to select.")


def find_opposite_by_name(node):
    """Return the node whose name has the side swapped, or None."""
    short = _short_name(node)
    opposite = mgear_string.convertRLName(short)
    if opposite == short:
        return None

    matches = cmds.ls(opposite, long=True)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        top = node.split("|")[1]
        same_top = [m for m in matches if m.split("|")[1] == top]
        if len(same_top) == 1:
            return same_top[0]
    return None


def _get_scope_root(node):
    """Return the guide model above node, or the top level ancestor."""
    parts = node.split("|")
    for depth in range(len(parts), 1, -1):
        candidate = "|".join(parts[:depth])
        if cmds.objExists(f"{candidate}.ismodel"):
            return candidate
    return "|".join(parts[:2])


def _list_scope_transforms(scope_root, cache):
    if scope_root in cache:
        return cache[scope_root]

    nodes = [scope_root]
    nodes += (
        cmds.listRelatives(
            scope_root, allDescendents=True, type="transform", fullPath=True
        )
    )
    entries = []
    for candidate in nodes:
        if not cmds.listRelatives(candidate, shapes=True, noIntermediate=True):
            continue
        position = cmds.xform(candidate, q=True, ws=True, t=True)
        entries.append((candidate, position))
    cache[scope_root] = entries
    return entries


def find_opposite_by_position(node, cache=None):
    """Return the node nearest to the node position mirrored on the YZ plane."""
    cache = {} if cache is None else cache
    position = cmds.xform(node, q=True, ws=True, t=True)
    if abs(position[0]) <= _AXIS_TOLERANCE:
        return None

    target = (-position[0], position[1], position[2])
    best = None
    best_distance = _POSITION_TOLERANCE
    for candidate, cand_pos in _list_scope_transforms(
        _get_scope_root(node), cache
    ):
        if candidate == node:
            continue
        distance = sum((a - b) ** 2 for a, b in zip(cand_pos, target)) ** 0.5
        if distance <= best_distance:
            best = candidate
            best_distance = distance
    return best


def select_opposite_side(by_position=False, add=False):
    """Select the opposite side nodes of the current selection.

    Args:
        by_position (bool): Match by mirrored position instead of name.
        add (bool): Keep the current selection and add the opposite nodes.
    """
    selection = _get_selection()
    if not selection:
        return

    cache = {}
    found = []
    missing = []
    for node in selection:
        if by_position:
            opposite = find_opposite_by_position(node, cache)
        else:
            opposite = find_opposite_by_name(node)
        if opposite:
            found.append(opposite)
        else:
            missing.append(node)

    label = "Opposite (position)" if by_position else "Opposite (name)"
    _report(found, missing, label)
    _apply_selection(found, add)


def _list_component_nodes(root):
    """Return the component root and its own locators (no nested components)."""
    nodes = [root]
    descendants = cmds.listRelatives(
        root, allDescendents=True, type="transform", fullPath=True
    )
    for node in descendants or []:
        if cmds.attributeQuery("comp_type", node=node, exists=True):
            continue
        if bridge.get_parent_component_root(node) != root:
            continue
        if not cmds.listRelatives(node, shapes=True, noIntermediate=True):
            continue
        nodes.append(node)
    return nodes


def select_component(roots_only=False):
    """Select the component of each selected guide node.

    Args:
        roots_only (bool): Select component roots only.
    """
    selection = _get_selection()
    if not selection:
        return

    roots = []
    for node in selection:
        root = bridge.get_component_root(node)
        if root and root not in roots:
            roots.append(root)
    if not roots:
        cmds.warning("No component found in selection.")
        return

    if roots_only:
        _apply_selection(roots, add=False)
        return

    nodes = []
    for root in roots:
        nodes.extend(_list_component_nodes(root))
    _apply_selection(nodes, add=False)


def select_child_components(recursive=False):
    """Select child component roots of the selected components.

    Args:
        recursive (bool): Include all nested components.
    """
    selection = _get_selection()
    if not selection:
        return

    roots = []
    for node in selection:
        root = bridge.get_component_root(node)
        if root and root not in roots:
            roots.append(root)
    if not roots:
        cmds.warning("No component found in selection.")
        return

    result = []
    pending = list(roots)
    while pending:
        current = pending.pop()
        for child in bridge.list_child_component_roots(current):
            if child not in result:
                result.append(child)
                if recursive:
                    pending.append(child)

    if not result:
        cmds.warning("No child components found.")
        return
    _apply_selection(result, add=False)


def _component_prefix(root):
    """Return the name prefix shared by a component guide and its controls."""
    short = _short_name(root)
    if short.endswith("_root"):
        return short[: -len("_root")]
    return None


def _list_controls_by_prefix(prefix):
    controls = []
    for rig_root in bridge._list_built_rig_transforms():
        for control in bridge._list_rig_control_nodes(rig_root):
            if _short_name(control).startswith(prefix + "_"):
                controls.append(control)
    return controls


def _is_control(node):
    return cmds.attributeQuery("isCtl", node=node, exists=True)


def _controls_from_guides(nodes):
    controls = []
    for node in nodes:
        root = bridge.get_component_root(node)
        prefix = _component_prefix(root) if root else None
        if prefix:
            controls.extend(_list_controls_by_prefix(prefix))
    return controls


def _guides_from_controls(nodes):
    guide_roots = {}
    for model in cmds.ls("*.ismodel", long=True, objectsOnly=True) or []:
        descendants = cmds.listRelatives(
            model, allDescendents=True, type="transform", fullPath=True
        )
        for node in descendants or []:
            if not cmds.attributeQuery("comp_type", node=node, exists=True):
                continue
            prefix = _component_prefix(node)
            if prefix:
                guide_roots[prefix] = node

    result = []
    for node in nodes:
        short = _short_name(node)
        matches = [p for p in guide_roots if short.startswith(p + "_")]
        if matches:
            result.append(guide_roots[max(matches, key=len)])
    return result


def toggle_guide_control(add=False):
    """Switch between guides and controls by the selection type.

    Selected controls (isCtl) become their guide component roots. Any other
    selected node becomes the built controls of its guide component. A mixed
    selection is converted node by node.

    Args:
        add (bool): Keep the current selection and add the counterparts.
    """
    selection = _get_selection()
    if not selection:
        return

    ctl_nodes = [n for n in selection if _is_control(n)]
    guide_nodes = [n for n in selection if not _is_control(n)]

    result = []
    if guide_nodes:
        if bridge.has_built_rig():
            result.extend(_controls_from_guides(guide_nodes))
        elif not ctl_nodes:
            cmds.warning("No built rig found.")
            return
    if ctl_nodes:
        result.extend(_guides_from_controls(ctl_nodes))

    if not result:
        cmds.warning("No counterpart found for the selection.")
        return
    _apply_selection(result, add=add)
