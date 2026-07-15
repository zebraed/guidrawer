from maya import cmds

from . import exception
from . import guide_align
from . import controller_shape_tools
from . import loader
from . import shifter_bridge as bridge


def _component_display_sort_key(name):
    """Sort key: lowercase-first (a-z), then uppercase-first (A-Z)."""
    if not name:
        return (0, name)
    if name[0].isupper():
        return (1, name.lower())
    return (0, name.lower())


class Guidrawer:
    """Main class for guide drawing.

    Can draw any component type recognized by mGear via a generic flow.
    Place preset modules under component/ to add components with custom
    draw behavior.
    """

    def __init__(self):
        self._presets = loader.load_presets()

    def reload_presets(self):
        self._presets = loader.load_presets()

    def list_component_name(self):
        """Return names of drawable components.

        Lists mGear types (a-z, then A-Z), then custom presets.
        """
        preset_names = set(self._presets.keys())
        names = [
            comp_type
            for comp_type in bridge.list_component_types()
            if comp_type not in preset_names
        ]
        names.sort(key=_component_display_sort_key)
        for preset_name in self._presets.keys():
            names.append(preset_name)
        return names

    def is_chain(self, comp_type):
        """Return whether the component is chain-like (needs section count)."""
        preset = self._presets.get(comp_type)
        if preset:
            comp_type = preset.COMPONENT_TYPE
        return bridge.is_chain_type(comp_type)

    def get_mgear_comp_type(self, comp_type):
        preset = self._presets.get(comp_type)
        if preset:
            return preset.COMPONENT_TYPE
        return comp_type

    def get_component_name(self, comp_type, name):
        if name:
            return name
        return bridge.get_default_name(self.get_mgear_comp_type(comp_type))

    def get_next_component_index(
        self, comp_type, name, side, parent_root, start_index=0
    ):
        """Return the next valid component index for the given properties."""
        return bridge.get_next_component_index(
            self.get_component_name(comp_type, name),
            side,
            self.get_mgear_comp_type(comp_type),
            parent_root,
            start_index,
        )

    def create_guide(self, comp_type, name, side, parent_root, idx=0, **opt):
        """Draw a guide component.

        Args:
            comp_type (str): Component type or preset name.
            name (str): Component name. Empty uses mGear default name.
            side (str): Side (C / L / R).
            parent_root (str): Parent guide node name. Empty uses guide model
                in the scene, or creates a new guide hierarchy if none exists.
            idx (int): Component index.
            **opt: Reserved for preset modules.

        Returns:
            str or None: New guide root name.
        """
        draw_parent = bridge.resolve_draw_parent(parent_root)
        if parent_root and str(parent_root).strip() and not draw_parent:
            return None

        preset = self._presets.get(comp_type)
        if preset:
            return preset.draw_guide(name, side, idx, draw_parent, **opt)

        if comp_type not in bridge.list_component_types():
            raise exception.ComponentNotFoundError(
                f"Not found comp type. : {comp_type}"
            )

        mgear_type = comp_type
        chain_opt = None
        if self.is_chain(comp_type):
            chain_opt = bridge.get_pre_settings_chain_opt(mgear_type)

        guide_root = bridge.draw_component(
            draw_parent, mgear_type, chain_opt
        )
        if not guide_root:
            return None

        if not name:
            name = bridge.get_default_name(comp_type)
        return bridge.rename_component(guide_root, name, side, idx)

    def has_pre_settings(self, comp_type):
        """Return whether the component type supports pre-settings UI."""
        return bridge.has_component_settings(
            self.get_mgear_comp_type(comp_type)
        )

    def open_pre_settings(self, comp_type, parent_root):
        """Open pre-settings UI for the selected component type."""
        parent_root = bridge.validate_guide(parent_root)
        if not parent_root:
            cmds.warning("Set a valid parent guide.")
            return None

        mgear_type = self.get_mgear_comp_type(comp_type)
        return bridge.open_pre_settings(mgear_type, parent_root)

    def has_pre_settings_cache(self, comp_type):
        """Return whether pre-settings are stored for the component type."""
        mgear_type = self.get_mgear_comp_type(comp_type)
        return bridge.has_pre_settings_cache(mgear_type)

    def reset_pre_settings(self, comp_type):
        """Discard stored pre-settings for the component type."""
        mgear_type = self.get_mgear_comp_type(comp_type)
        return bridge.reset_pre_settings(mgear_type)

    def apply_pre_settings(self, comp_type, guide_root):
        """Copy pre-settings onto guide_root after creation."""
        if not guide_root:
            return False

        mgear_type = self.get_mgear_comp_type(comp_type)
        return bridge.apply_pre_settings(mgear_type, guide_root)

    def duplicate_guide(self, nodes, symmetrize=False):
        """Find component root from selected nodes and duplicate."""
        if not nodes:
            cmds.warning("Nothing selected.")
            return
        for node in nodes:
            root = bridge.get_component_root(node)
            if root:
                bridge.duplicate_component(root, symmetrize)
            else:
                cmds.warning("Can not got guide root.")

    def _list_guide_roots(self, nodes):
        roots = []
        for node in nodes:
            root = bridge.get_component_root(node)
            if not root:
                cmds.warning("Can not got guide root.")
                continue
            if root not in roots:
                roots.append(root)
        return roots

    def delete_guide(self, nodes):
        """Find component root from selected nodes and delete."""
        if not nodes:
            cmds.warning("Nothing selected.")
            return
        for root in self._list_guide_roots(nodes):
            if cmds.objExists(root):
                bridge.delete_component(root)

    def delete_guide_keep_children(self, nodes):
        """Delete component roots and keep nested child components."""
        if not nodes:
            cmds.warning("Nothing selected.")
            return
        for root in self._list_guide_roots(nodes):
            if cmds.objExists(root):
                bridge.delete_component_keep_children(root)

    def open_settings(self, nodes):
        """Open the mGear settings UI for the first selected guide or component."""
        bridge.open_settings_from_selection(nodes)

    def extract_controls(self):
        """Extract selected controls, or all rig controls when nothing or rig root is selected."""
        bridge.extract_controls()

    def update_component_type(self):
        """Open mGear Update Component Type UI for the current selection."""
        bridge.update_component_type()

    def open_guide_symmetry_tool(self):
        bridge.open_guide_symmetry_tool()

    def open_component_type_lister(self):
        bridge.open_component_type_lister()

    def open_chain_utils(self):
        bridge.open_chain_utils()

    def vanilla_build_guide(self):
        """Build from selection without pre/post custom steps (mGear-like)."""
        bridge.vanilla_build_guide()

    def has_full_build_steps(self):
        """Return whether the scene guide has pre or post custom scripts."""
        return bridge.has_full_build_steps()

    def has_built_rig(self):
        """Return whether the scene contains a built mGear rig."""
        return bridge.has_built_rig()

    def full_build_guide(self, with_log=False):
        """Build rig from guide with pre/post custom steps enabled."""
        bridge.full_build_guide(with_log=with_log)

    def unbuild_guide(self):
        """Unbuild the current rig in the scene."""
        bridge.unbuild_guide()

    def fit_to_pos(self):
        guide_align.fit_to_pos()

    def align_mid_pos(self):
        guide_align.align_mid_pos()

    def fit_nearest(self):
        guide_align.fit_nearest()

    def align_rot(self):
        guide_align.align_rot()

    def align_mid_rot(self):
        guide_align.align_mid_rot()

    def align_rot_nearest(self):
        guide_align.align_rot_nearest()

    def aim_x(self):
        guide_align.aim_x()

    def aim_y(self):
        guide_align.aim_y()

    def aim_z(self):
        guide_align.aim_z()

    def rotate_axis(self, axis, degrees):
        guide_align.rotate_selected(axis, degrees)

    def align_curve(self):
        guide_align.align_curve()

    def get_preserve_children(self):
        """Return Preserve Children state for Move/Rotate/Scale tools."""
        return cmds.manipMoveContext("Move", q=True, pcp=True)

    def set_preserve_children(self, enabled):
        """Set Preserve Children on Move, Rotate, and Scale manip contexts."""
        cmds.manipMoveContext("Move", e=True, pcp=enabled)
        cmds.manipRotateContext("Rotate", e=True, pcp=enabled)
        cmds.manipScaleContext("Scale", e=True, pcp=enabled)

    def select_controller_shapes(self):
        controller_shape_tools.select_controller_shapes()

    def scale_controller_shapes(self, delta):
        controller_shape_tools.scale_shapes(delta)

    def toggle_controller_edit_mode(self):
        controller_shape_tools.toggle_edit_mode()

    def replace_control_shape(self):
        bridge.replace_control_shape()

    def mirror_control_shape(self):
        bridge.mirror_control_shape()
