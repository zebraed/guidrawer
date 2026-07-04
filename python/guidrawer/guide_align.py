"""Guide position and rotation alignment utilities for mGear guides."""
import math
import re

from maya import cmds
import maya.api.OpenMaya as om


_SURFACE_SHAPE_TYPES = ("mesh", "nurbsCurve", "nurbsSurface")
_COMPONENT_PATTERN = re.compile(
    r"\.(vtx\[|e\[|f\[|cv\[|u\[|v\[|map\[)"
)


def _vec_add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _vec_sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _vec_scale(v, s):
    return [v[0] * s, v[1] * s, v[2] * s]


def _vec_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_length(v):
    return math.sqrt(_vec_dot(v, v))


def _vec_normalize(v):
    length = _vec_length(v)
    if length < 1e-8:
        return None
    return _vec_scale(v, 1.0 / length)


def _average_vectors(vectors):
    if not vectors:
        return None
    total = [0.0, 0.0, 0.0]
    for vec in vectors:
        total = _vec_add(total, vec)
    count = float(len(vectors))
    return _vec_scale(total, 1.0 / count)


def _perpendicular_axis(axis):
    axis = _vec_normalize(axis)
    if not axis:
        return [1.0, 0.0, 0.0]
    candidate = [0.0, 1.0, 0.0]
    if abs(_vec_dot(axis, candidate)) > 0.9:
        candidate = [1.0, 0.0, 0.0]
    return _vec_normalize(_vec_sub(candidate, _vec_scale(axis, _vec_dot(candidate, axis))))


def _is_component(name):
    return bool(_COMPONENT_PATTERN.search(name))


def _get_selection():
    selection = cmds.ls(sl=True, fl=True)
    if not selection:
        cmds.warning("Nothing selected.")
        return None
    return selection


def _get_preserve_children():
    try:
        return cmds.manipMoveContext("Move", q=True, pcp=True)
    except RuntimeError:
        return False


def _get_world_matrix(node):
    return cmds.xform(node, q=True, m=True, ws=True)


def _get_world_translation(node):
    matrix = _get_world_matrix(node)
    return [matrix[12], matrix[13], matrix[14]]


def _move_world_delta(node, delta, preserve_children=None):
    if preserve_children is None:
        preserve_children = _get_preserve_children()
    if (
        abs(delta[0]) < 1e-8
        and abs(delta[1]) < 1e-8
        and abs(delta[2]) < 1e-8
    ):
        return
    cmds.move(
        delta[0],
        delta[1],
        delta[2],
        node,
        r=True,
        ws=True,
        pcp=preserve_children,
    )


def _set_world_translation(node, position):
    preserve_children = _get_preserve_children()
    if preserve_children:
        current = _get_world_translation(node)
        delta = [
            position[0] - current[0],
            position[1] - current[1],
            position[2] - current[2],
        ]
        _move_world_delta(node, delta, preserve_children=True)
        return

    matrix = _get_world_matrix(node)
    matrix[12] = position[0]
    matrix[13] = position[1]
    matrix[14] = position[2]
    cmds.xform(node, m=matrix, ws=True)


def _get_world_rotation(node):
    return cmds.xform(node, q=True, ro=True, ws=True)


def _set_world_rotation_preserve_position(node, rotation):
    position = _get_world_translation(node)
    preserve_children = _get_preserve_children()
    if preserve_children:
        cmds.rotate(
            rotation[0],
            rotation[1],
            rotation[2],
            node,
            ws=True,
            a=True,
            pcp=True,
        )
        current = _get_world_translation(node)
        delta = [
            position[0] - current[0],
            position[1] - current[1],
            position[2] - current[2],
        ]
        _move_world_delta(node, delta, preserve_children=True)
        return

    cmds.xform(node, t=position, ro=rotation, ws=True)


def _get_transform_node(node):
    if _is_component(node):
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        if parents:
            return parents[0]
        return None
    return node


def _get_surface_shape(node):
    if _is_component(node):
        parents = cmds.listRelatives(node, parent=True, fullPath=True, type="shape")
        if not parents:
            dag = cmds.listRelatives(node, parent=True, fullPath=True)
            if dag:
                shapes = cmds.listRelatives(
                    dag[0], shapes=True, ni=True, fullPath=True
                )
                if shapes:
                    parents = shapes
        if parents and cmds.nodeType(parents[0]) in _SURFACE_SHAPE_TYPES:
            return parents[0]
        return None

    node_type = cmds.nodeType(node)
    if node_type in _SURFACE_SHAPE_TYPES:
        return node

    shapes = cmds.listRelatives(node, shapes=True, ni=True, fullPath=True)
    if not shapes:
        return None
    for shape in shapes:
        if cmds.nodeType(shape) in _SURFACE_SHAPE_TYPES:
            return shape
    return None


def _parse_poly_normal(face):
    info = cmds.polyInfo(face, faceNormals=True)
    if not info:
        return None
    tokens = info[0].split()
    try:
        idx = tokens.index(":")
        return [float(tokens[idx + 1]), float(tokens[idx + 2]), float(tokens[idx + 3])]
    except (ValueError, IndexError):
        return None


def _get_vertex_normal(vertex):
    x_val = cmds.polyNormalPerVertex(vertex, q=True, ws=True, x=True)
    y_val = cmds.polyNormalPerVertex(vertex, q=True, ws=True, y=True)
    z_val = cmds.polyNormalPerVertex(vertex, q=True, ws=True, z=True)
    if not x_val:
        return None
    return _vec_normalize([x_val[0], y_val[0], z_val[0]])


def _get_edge_frame(edge):
    verts = cmds.ls(
        cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True),
        fl=True,
    )
    if len(verts) < 2:
        return None, None

    p0 = cmds.pointPosition(verts[0], w=True)
    p1 = cmds.pointPosition(verts[1], w=True)
    tangent = _vec_normalize(_vec_sub(p1, p0))
    if not tangent:
        return None, None

    faces = cmds.ls(
        cmds.polyListComponentConversion(edge, fromEdge=True, toFace=True),
        fl=True,
    )
    normals = []
    for face in faces:
        normal = _parse_poly_normal(face)
        if normal:
            normals.append(normal)

    normal = _average_vectors(normals)
    if not normal:
        normal = _perpendicular_axis(tangent)
    normal = _vec_normalize(normal)
    if not normal:
        return None, None

    tangent = _vec_normalize(
        _vec_sub(tangent, _vec_scale(normal, _vec_dot(tangent, normal)))
    )
    if not tangent:
        tangent = _perpendicular_axis(normal)
    return normal, tangent


def _get_face_frame(face):
    normal = _parse_poly_normal(face)
    if not normal:
        return None, None
    normal = _vec_normalize(normal)

    verts = cmds.ls(
        cmds.polyListComponentConversion(face, fromFace=True, toVertex=True),
        fl=True,
    )
    if len(verts) < 2:
        return normal, _perpendicular_axis(normal)

    p0 = cmds.pointPosition(verts[0], w=True)
    p1 = cmds.pointPosition(verts[1], w=True)
    tangent = _vec_normalize(_vec_sub(p1, p0))
    if tangent:
        tangent = _vec_normalize(
            _vec_sub(tangent, _vec_scale(normal, _vec_dot(tangent, normal)))
        )
    if not tangent:
        tangent = _perpendicular_axis(normal)
    return normal, tangent


def _get_surface_dag_path(node):
    """Return MDagPath to a surface shape under node."""
    if _is_component(node):
        node = _get_transform_node(node)
        if not node:
            return None

    node_type = cmds.nodeType(node)
    if node_type in _SURFACE_SHAPE_TYPES:
        target = node
    else:
        shapes = cmds.listRelatives(
            node,
            shapes=True,
            ni=True,
            fullPath=True,
            type=_SURFACE_SHAPE_TYPES,
        )
        if not shapes:
            return None
        target = shapes[0]

    selection = om.MSelectionList()
    selection.add(target)
    return selection.getDagPath(0)


def _mvector_to_list(vec):
    if vec is None:
        return None
    return [vec.x, vec.y, vec.z]


def _mpoint_to_list(point):
    return [point.x, point.y, point.z]


def _mesh_tangent_from_face(mesh_fn, face_id, normal):
    vtx_ids = mesh_fn.getPolygonVertices(face_id)
    if len(vtx_ids) < 2:
        return _perpendicular_axis(normal)

    p0 = mesh_fn.getPoint(vtx_ids[0], om.MSpace.kWorld)
    p1 = mesh_fn.getPoint(vtx_ids[1], om.MSpace.kWorld)
    tangent = _vec_normalize(_vec_sub(_mpoint_to_list(p1), _mpoint_to_list(p0)))
    if not tangent:
        return _perpendicular_axis(normal)

    tangent = _vec_normalize(
        _vec_sub(tangent, _vec_scale(normal, _vec_dot(tangent, normal)))
    )
    if not tangent:
        return _perpendicular_axis(normal)
    return tangent


def _get_mesh_closest_frame_api(dag_path, world_point):
    mesh_fn = om.MFnMesh(dag_path)
    query = om.MPoint(world_point[0], world_point[1], world_point[2])
    closest, _ = mesh_fn.getClosestPoint(query, om.MSpace.kWorld)
    position = _mpoint_to_list(closest)

    normal_vec, face_id = mesh_fn.getClosestNormal(query, om.MSpace.kWorld)
    normal = _vec_normalize(_mvector_to_list(normal_vec))
    if not normal:
        return position, None, None

    if face_id >= 0:
        tangent = _mesh_tangent_from_face(mesh_fn, face_id, normal)
    else:
        tangent = _perpendicular_axis(normal)
    return position, normal, tangent


def _as_float(value):
    if isinstance(value, (float, int)):
        return float(value)
    return None


def _curve_parameter_at_point(curve_fn, query):
    try:
        param = curve_fn.getParamAtPoint(query, om.MSpace.kWorld)
        float_param = _as_float(param)
        if float_param is not None:
            return float_param
    except (TypeError, RuntimeError):
        pass

    result = curve_fn.closestPoint(query, om.MSpace.kWorld)
    if isinstance(result, (tuple, list)):
        for item in result:
            if isinstance(item, om.MPoint):
                param = curve_fn.getParamAtPoint(item, om.MSpace.kWorld)
                float_param = _as_float(param)
                if float_param is not None:
                    return float_param
                continue
            float_param = _as_float(item)
            if float_param is not None:
                return float_param
        return None

    if isinstance(result, om.MPoint):
        param = curve_fn.getParamAtPoint(result, om.MSpace.kWorld)
        return _as_float(param)

    return _as_float(result)


def _get_nurbs_curve_closest_frame_api(dag_path, world_point):
    curve_fn = om.MFnNurbsCurve(dag_path)
    query = om.MPoint(world_point[0], world_point[1], world_point[2])
    param = _curve_parameter_at_point(curve_fn, query)
    if param is None:
        return None, None, None

    position = _mpoint_to_list(curve_fn.getPointAtParam(param, om.MSpace.kWorld))
    tangent_vec = curve_fn.tangent(param, om.MSpace.kWorld)
    if isinstance(tangent_vec, (tuple, list)):
        tangent_vec = tangent_vec[0]
    tangent = _vec_normalize(_mvector_to_list(tangent_vec))
    if not tangent:
        return position, None, None
    normal = _perpendicular_axis(tangent)
    return position, normal, tangent


def _nurbs_surface_closest_point_and_uv(surf_fn, query):
    try:
        result = surf_fn.closestPoint(
            query,
            None,
            None,
            False,
            1.0,
            om.MSpace.kWorld,
        )
    except TypeError:
        result = surf_fn.closestPoint(query, space=om.MSpace.kWorld)

    if isinstance(result, (tuple, list)):
        if len(result) >= 3:
            closest_point = result[0]
            u_param = _as_float(result[1])
            v_param = _as_float(result[2])
            return closest_point, u_param, v_param
        if len(result) == 2:
            closest_point = result[0]
            uv = result[1]
            if isinstance(uv, (tuple, list)) and len(uv) >= 2:
                return (
                    closest_point,
                    _as_float(uv[0]),
                    _as_float(uv[1]),
                )
        if len(result) == 1 and isinstance(result[0], om.MPoint):
            uv_point = result[0]
            return uv_point, uv_point.x, uv_point.y

    if isinstance(result, om.MPoint):
        return result, result.x, result.y

    return None, None, None


def _get_nurbs_surface_closest_frame_api(dag_path, world_point):
    surf_fn = om.MFnNurbsSurface(dag_path)
    query = om.MPoint(world_point[0], world_point[1], world_point[2])
    closest_point, u_param, v_param = _nurbs_surface_closest_point_and_uv(
        surf_fn, query
    )
    if u_param is None or v_param is None:
        return None, None, None

    if isinstance(closest_point, om.MPoint):
        position = _mpoint_to_list(closest_point)
    elif isinstance(closest_point, (tuple, list)) and len(closest_point) >= 3:
        position = [
            closest_point[0],
            closest_point[1],
            closest_point[2],
        ]
    else:
        position = _mpoint_to_list(
            surf_fn.getPointAtParam(u_param, v_param, om.MSpace.kWorld)
        )

    normal = _vec_normalize(_mvector_to_list(
        surf_fn.normal(u_param, v_param, om.MSpace.kWorld)
    ))
    tangent_result = surf_fn.tangents(u_param, v_param, om.MSpace.kWorld)
    if isinstance(tangent_result, (tuple, list)):
        u_tangent = tangent_result[0]
    else:
        u_tangent = tangent_result
    tangent = _vec_normalize(_mvector_to_list(u_tangent))
    if normal and not tangent:
        tangent = _perpendicular_axis(normal)
    return position, normal, tangent


def _get_closest_frame_on_surface(node, world_point):
    dag_path = _get_surface_dag_path(node)
    if not dag_path:
        return None, None, None

    shape_type = dag_path.apiType()
    if shape_type == om.MFn.kMesh:
        return _get_mesh_closest_frame_api(dag_path, world_point)
    if shape_type == om.MFn.kNurbsCurve:
        return _get_nurbs_curve_closest_frame_api(dag_path, world_point)
    if shape_type == om.MFn.kNurbsSurface:
        return _get_nurbs_surface_closest_frame_api(dag_path, world_point)
    return None, None, None


def _get_nurbs_curve_tangent(shape, world_point):
    dag_path = _get_surface_dag_path(shape)
    if not dag_path:
        return None
    _, _, tangent = _get_nurbs_curve_closest_frame_api(dag_path, world_point)
    return tangent


def _get_nurbs_surface_frame(shape, world_point):
    dag_path = _get_surface_dag_path(shape)
    if not dag_path:
        return None, None
    _, normal, tangent = _get_nurbs_surface_closest_frame_api(dag_path, world_point)
    return normal, tangent


def _get_component_frame(component):
    if ".vtx[" in component:
        normal = _get_vertex_normal(component)
        if not normal:
            return None, None
        position = cmds.pointPosition(component, w=True)
        tangent = _perpendicular_axis(normal)
        return normal, tangent

    if ".e[" in component:
        return _get_edge_frame(component)

    if ".f[" in component:
        return _get_face_frame(component)

    if ".cv[" in component:
        position = cmds.pointPosition(component, w=True)
        shape = _get_surface_shape(component)
        if not shape:
            return None, None
        shape_type = cmds.nodeType(shape)
        if shape_type == "nurbsCurve":
            tangent = _get_nurbs_curve_tangent(shape, position)
            if not tangent:
                return None, None
            normal = _perpendicular_axis(tangent)
            return normal, tangent
        if shape_type == "nurbsSurface":
            return _get_nurbs_surface_frame(shape, position)

    return None, None


def _vec_cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _rotation_from_normal_tangent(normal, tangent):
    z_axis = _vec_normalize(normal)
    if not z_axis:
        return None

    x_axis = _vec_normalize(tangent)
    if x_axis:
        x_axis = _vec_normalize(
            _vec_sub(x_axis, _vec_scale(z_axis, _vec_dot(x_axis, z_axis)))
        )
    if not x_axis:
        x_axis = _perpendicular_axis(z_axis)

    y_axis = _vec_normalize(_vec_cross(z_axis, x_axis))
    x_axis = _vec_normalize(_vec_cross(y_axis, z_axis))

    matrix = om.MMatrix([
        x_axis[0], x_axis[1], x_axis[2], 0.0,
        y_axis[0], y_axis[1], y_axis[2], 0.0,
        z_axis[0], z_axis[1], z_axis[2], 0.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    rotation = om.MTransformationMatrix(matrix).rotation()
    return [
        om.MAngle(rotation.x).asDegrees(),
        om.MAngle(rotation.y).asDegrees(),
        om.MAngle(rotation.z).asDegrees(),
    ]


def _quaternion_dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w


def _average_rotations(nodes):
    if not nodes:
        return None

    quaternions = []
    for node in nodes:
        matrix = om.MMatrix(cmds.xform(node, q=True, m=True, ws=True))
        rotation = om.MTransformationMatrix(matrix).rotation()
        quaternions.append(rotation.asQuaternion())

    if not quaternions:
        return None

    reference = quaternions[0]
    summed = om.MQuaternion(0.0, 0.0, 0.0, 0.0)
    for quat in quaternions:
        if _quaternion_dot(quat, reference) < 0.0:
            quat = -quat
        summed = summed + quat

    if abs(summed.w) < 1e-8 and abs(summed.x) < 1e-8:
        return _get_world_rotation(nodes[0])

    summed.normalizeIt()
    euler = summed.asEulerRotation()
    return [
        om.MAngle(euler.x).asDegrees(),
        om.MAngle(euler.y).asDegrees(),
        om.MAngle(euler.z).asDegrees(),
    ]


def fit_to_pos():
    """Move guides to the last selection's world position."""
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select one or more guides, then a fit target.")
        return

    reference = selection[-1]
    target_pos = _get_world_translation(reference)
    for node in selection[:-1]:
        target = _get_transform_node(node)
        if target:
            _set_world_translation(target, target_pos)


def align_mid_pos():
    """Move the last selection to the average position of the others."""
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select two or more elements.")
        return

    last_node = selection[-1]
    others = selection[:-1]
    positions = []
    for node in others:
        positions.append(_get_world_translation(node))

    average_pos = _average_vectors(positions)
    if not average_pos:
        return

    target = _get_transform_node(last_node)
    if target:
        _set_world_translation(target, average_pos)


def fit_nearest():
    """Move guides to the closest point on the last surface selection."""
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select one or more guides, then a fit target surface.")
        return

    surface = selection[-1]
    if not _get_surface_dag_path(surface):
        cmds.warning(
            "Last selection must be a polygon mesh, nurbsCurve, or nurbsSurface."
        )
        return

    for node in selection[:-1]:
        target = _get_transform_node(node)
        if not target:
            continue
        source_pos = _get_world_translation(target)
        position, _, _ = _get_closest_frame_on_surface(surface, source_pos)
        if position:
            _set_world_translation(target, position)


def align_rot():
    """Align guide rotation to the last selection."""
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select one or more guides, then a fit target.")
        return

    reference = selection[-1]
    targets = selection[:-1]

    if _is_component(reference):
        normal, tangent = _get_component_frame(reference)
        if not normal or not tangent:
            cmds.warning("Could not get normal and tangent from component.")
            return
        rotation = _rotation_from_normal_tangent(normal, tangent)
        if not rotation:
            cmds.warning("Could not build rotation from component.")
            return
        for node in targets:
            target = _get_transform_node(node)
            if target:
                _set_world_rotation_preserve_position(target, rotation)
        return

    rotation = _get_world_rotation(reference)
    for node in targets:
        target = _get_transform_node(node)
        if target:
            _set_world_rotation_preserve_position(target, rotation)


def align_mid_rot():
    """Rotate the last selection to the average rotation of the others."""
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select two or more elements.")
        return

    last_node = selection[-1]
    others = selection[:-1]
    transform_nodes = []
    for node in others:
        target = _get_transform_node(node)
        if target:
            transform_nodes.append(target)

    rotation = _average_rotations(transform_nodes)
    if not rotation:
        return

    target = _get_transform_node(last_node)
    if target:
        _set_world_rotation_preserve_position(target, rotation)


def align_rot_nearest():
    """Align guide rotation to the closest surface Normal/Tangent."""
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select one or more guides, then a fit target surface.")
        return

    surface = selection[-1]
    if not _get_surface_dag_path(surface):
        cmds.warning(
            "Last selection must be a polygon mesh, nurbsCurve, or nurbsSurface."
        )
        return

    for node in selection[:-1]:
        target = _get_transform_node(node)
        if not target:
            continue
        source_pos = _get_world_translation(target)
        _, normal, tangent = _get_closest_frame_on_surface(surface, source_pos)
        if not normal or not tangent:
            continue
        rotation = _rotation_from_normal_tangent(normal, tangent)
        if rotation:
            _set_world_rotation_preserve_position(target, rotation)


_AIM_UP_HINTS = {
    "x": [0.0, 1.0, 0.0],
    "y": [0.0, 0.0, 1.0],
    "z": [1.0, 0.0, 0.0],
}


def _matrix_to_euler_degrees(matrix):
    rotation = om.MTransformationMatrix(matrix).rotation()
    return [
        om.MAngle(rotation.x).asDegrees(),
        om.MAngle(rotation.y).asDegrees(),
        om.MAngle(rotation.z).asDegrees(),
    ]


def _rotation_aim_at(source_pos, target_pos, aim_axis):
    aim_dir = _vec_normalize(_vec_sub(target_pos, source_pos))
    if not aim_dir:
        return None

    up_hint = _AIM_UP_HINTS[aim_axis]

    if aim_axis == "x":
        x_axis = aim_dir
        z_axis = _vec_normalize(_vec_cross(x_axis, up_hint))
        if not z_axis:
            z_axis = [0.0, 0.0, 1.0]
        y_axis = _vec_normalize(_vec_cross(z_axis, x_axis))
        z_axis = _vec_normalize(_vec_cross(x_axis, y_axis))
    elif aim_axis == "y":
        y_axis = aim_dir
        x_axis = _vec_normalize(_vec_cross(up_hint, y_axis))
        if not x_axis:
            x_axis = [1.0, 0.0, 0.0]
        z_axis = _vec_normalize(_vec_cross(x_axis, y_axis))
        x_axis = _vec_normalize(_vec_cross(y_axis, z_axis))
    else:
        z_axis = aim_dir
        y_axis = _vec_normalize(_vec_cross(z_axis, up_hint))
        if not y_axis:
            y_axis = [0.0, 1.0, 0.0]
        x_axis = _vec_normalize(_vec_cross(y_axis, z_axis))
        y_axis = _vec_normalize(_vec_cross(z_axis, x_axis))

    matrix = om.MMatrix([
        x_axis[0], x_axis[1], x_axis[2], 0.0,
        y_axis[0], y_axis[1], y_axis[2], 0.0,
        z_axis[0], z_axis[1], z_axis[2], 0.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    return _matrix_to_euler_degrees(matrix)


def _aim(axis_key):
    selection = _get_selection()
    if not selection:
        return
    if len(selection) < 2:
        cmds.warning("Select one or more guides, then an aim target.")
        return

    reference = _get_transform_node(selection[-1])
    if not reference:
        cmds.warning("Invalid aim target.")
        return
    target_pos = _get_world_translation(reference)

    for node in selection[:-1]:
        guide = _get_transform_node(node)
        if not guide:
            continue
        source_pos = _get_world_translation(guide)
        rotation = _rotation_aim_at(source_pos, target_pos, axis_key)
        if rotation:
            _set_world_rotation_preserve_position(guide, rotation)


def aim_x():
    """Aim guide X axis toward the last selection. Y is up."""
    _aim("x")


def aim_y():
    """Aim guide Y axis toward the last selection. Z is up."""
    _aim("y")


def aim_z():
    """Aim guide Z axis toward the last selection. X is up."""
    _aim("z")


def _local_axis_euler_rotation(axis, degrees):
    radians = math.radians(degrees)
    if axis == "x":
        return om.MEulerRotation(radians, 0.0, 0.0)
    if axis == "y":
        return om.MEulerRotation(0.0, radians, 0.0)
    return om.MEulerRotation(0.0, 0.0, radians)


def _normalize_local_rotate_attr(node):
    rotate_order = cmds.getAttr("{}.rotateOrder".format(node))
    matrix = om.MMatrix(cmds.xform(node, q=True, m=True, os=True))
    quat = om.MTransformationMatrix(matrix).rotation().asQuaternion()
    quat.normalizeIt()
    euler = quat.asEulerRotation()
    euler.reorderIt(rotate_order)
    cmds.setAttr(
        "{}.rotate".format(node),
        om.MAngle(euler.x).asDegrees(),
        om.MAngle(euler.y).asDegrees(),
        om.MAngle(euler.z).asDegrees(),
    )


def rotate_selected(axis, degrees):
    """Rotate around a local X/Y/Z axis via object-space matrix."""
    selection = _get_selection()
    if not selection:
        return

    axis_key = axis.lower()
    if axis_key not in ("x", "y", "z"):
        return

    preserve_children = _get_preserve_children()
    if preserve_children:
        if axis_key == "x":
            rotate_values = (degrees, 0.0, 0.0)
        elif axis_key == "y":
            rotate_values = (0.0, degrees, 0.0)
        else:
            rotate_values = (0.0, 0.0, degrees)

        for node in selection:
            target = _get_transform_node(node)
            if not target:
                continue
            if not cmds.objExists("{}.rotate".format(target)):
                continue
            cmds.rotate(
                rotate_values[0],
                rotate_values[1],
                rotate_values[2],
                target,
                r=True,
                os=True,
                pcp=True,
            )
            _normalize_local_rotate_attr(target)
        return

    delta = _local_axis_euler_rotation(axis_key, degrees)

    for node in selection:
        target = _get_transform_node(node)
        if not target:
            continue
        if not cmds.objExists("{}.rotate".format(target)):
            continue

        matrix = om.MMatrix(cmds.xform(target, q=True, m=True, os=True))
        tm = om.MTransformationMatrix(matrix)
        tm.rotateBy(delta, om.MSpace.kObject)
        cmds.xform(target, m=list(tm.asMatrix()), os=True)
        _normalize_local_rotate_attr(target)
