"""Controller shape utilities for mGear controls."""
import re

from maya import cmds


_COMPONENT_PATTERN = re.compile(
    r"\.(vtx\[|e\[|f\[|cv\[|u\[|v\[|map\[|p\[|uv\[)"
)
_SCALEABLE_SHAPE_TYPES = ("nurbsCurve", "nurbsSurface", "mesh")


def _is_shape_component(name):
    return bool(_COMPONENT_PATTERN.search(name))


def _is_shape_node(node):
    return cmds.objectType(node, isAType="shape")


def _get_shape_from_component(name):
    return name.split(".", 1)[0]


def _list_shapes_for_select(nodes):
    """Return shape nodes to select from controller transforms."""
    shapes = []
    seen = set()
    for node in nodes:
        if _is_shape_node(node):
            if node not in seen:
                shapes.append(node)
                seen.add(node)
            continue
        if _is_shape_component(node):
            shape = _get_shape_from_component(node)
            if shape not in seen:
                shapes.append(shape)
                seen.add(shape)
            continue
        if not cmds.objExists(node):
            continue
        found = cmds.listRelatives(
            node,
            shapes=True,
            fullPath=True,
            noIntermediate=True,
        )
        if not found:
            continue
        for shape in found:
            if shape not in seen:
                shapes.append(shape)
                seen.add(shape)
    return shapes


def _list_shapes_for_scale(nodes):
    """Return shape nodes to scale, including all shapes under transforms."""
    shapes = []
    seen = set()
    for node in nodes:
        if _is_shape_node(node):
            if node not in seen:
                shapes.append(node)
                seen.add(node)
            continue
        if _is_shape_component(node):
            shape = _get_shape_from_component(node)
            if shape not in seen:
                shapes.append(shape)
                seen.add(shape)
            continue
        if not cmds.objExists(node):
            continue
        found = cmds.listRelatives(
            node,
            shapes=True,
            fullPath=True,
            allDescendents=True,
            noIntermediate=True,
        )
        if not found:
            continue
        for shape in found:
            if shape not in seen:
                shapes.append(shape)
                seen.add(shape)
    return shapes


def _get_scale_components(shape):
    node_type = cmds.nodeType(shape)
    if node_type == "nurbsCurve":
        return cmds.ls("{}.cv[*]".format(shape), fl=True)
    if node_type == "nurbsSurface":
        return cmds.ls("{}.cv[*]".format(shape), fl=True)
    if node_type == "mesh":
        return cmds.ls("{}.vtx[*]".format(shape), fl=True)
    return []


def _scale_shape_components(shape, factor):
    node_type = cmds.nodeType(shape)
    if node_type not in _SCALEABLE_SHAPE_TYPES:
        return False

    components = _get_scale_components(shape)
    if not components:
        return False

    for component in components:
        position = cmds.xform(component, q=True, os=True, t=True)
        scaled = [
            position[0] * factor,
            position[1] * factor,
            position[2] * factor,
        ]
        cmds.xform(component, os=True, t=scaled)
    return True


def select_controller_shapes():
    """Select shape nodes from the current controller selection."""
    sel = cmds.ls(sl=True, long=True)
    if not sel:
        cmds.warning("Nothing selected.")
        return

    shapes = _list_shapes_for_select(sel)
    if not shapes:
        cmds.warning("No controller shapes found in selection.")
        return

    cmds.select(shapes, r=True)


def scale_shapes(delta):
    """Scale selected shapes in object space by the given delta.

    Args:
        delta (float): Scale delta. +0.1 scales up by 10%, -0.1 scales down.
    """
    sel = cmds.ls(sl=True, long=True)
    if not sel:
        cmds.warning("Nothing selected.")
        return

    shapes = _list_shapes_for_scale(sel)
    if not shapes:
        cmds.warning("No shapes found in selection.")
        return

    factor = 1.0 + delta
    if factor <= 0.0:
        cmds.warning("Scale factor must be greater than zero.")
        return

    scaled_any = False
    for shape in shapes:
        if _scale_shape_components(shape, factor):
            scaled_any = True

    if scaled_any:
        cmds.select(shapes, r=True)
    else:
        cmds.warning("No scaleable shapes found in selection.")


def _list_parent_transforms(nodes):
    """Return unique parent transforms for shapes or components."""
    trs = []
    seen = set()
    for node in nodes:
        base = node.split(".", 1)[0]
        if not cmds.objExists(base):
            continue
        if _is_shape_node(base):
            parents = cmds.listRelatives(base, parent=True, fullPath=True)
            if not parents:
                continue
            transform = parents[0]
        else:
            transform = base
        if transform not in seen:
            trs.append(transform)
            seen.add(transform)
    return trs


def toggle_edit_mode():
    """Toggle Maya selection between object and component mode.

    Leaving component mode selects parent transforms so Extr. Ctrl can run next.
    """
    if cmds.selectMode(q=True, component=True):
        sel = cmds.ls(sl=True, long=True)
        trs = _list_parent_transforms(sel)
        cmds.selectMode(object=True)
        if trs:
            cmds.select(trs, r=True)
    else:
        cmds.selectMode(component=True)
