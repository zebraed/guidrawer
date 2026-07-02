from maya import cmds

from . import exception
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
            parent_root (str): Parent guide node name.
            idx (int): Component index.
            **opt: For chain types: sections_number, dir_axis, spacing.

        Returns:
            str or None: New guide root name.
        """
        parent_root = bridge.validate_guide(parent_root)
        if not parent_root:
            return None

        preset = self._presets.get(comp_type)
        if preset:
            return preset.draw_guide(name, side, idx, parent_root, **opt)

        if comp_type not in bridge.list_component_types():
            raise exception.ComponentNotFoundError(
                f"Not found comp type. : {comp_type}"
            )

        chain_opt = None
        if self.is_chain(comp_type):
            chain_opt = opt

        guide_root = bridge.draw_component(parent_root, comp_type, chain_opt)
        if not guide_root:
            return None

        if not name:
            name = bridge.get_default_name(comp_type)
        return bridge.rename_component(guide_root, name, side, idx)

    def duplicate_guide(self, nodes, symmetrize=False):
        """Find component root from selected nodes and duplicate."""
        for node in nodes:
            root = bridge.get_component_root(node)
            if root:
                bridge.duplicate_component(root, symmetrize)
            else:
                cmds.warning("Can not got guide root.")
