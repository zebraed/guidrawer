from . import base
from . import exception
from . import loader


class Guidrawer(base.GuidrawerBase):
    """Draw main class."""

    def __init__(self):
        super().__init__()
        self.__loader = loader.Loader()
        self.modules = None
        self.component_type = None
        self.comp_guide = None
        self.reload_module()

    def reload_module(self):
        self.modules = self.__loader.load_component()

    def list_component_name(self):
        return list(self.modules.keys())

    def load_component(self, component_type):
        if component_type in self.modules:
            _mod = self.modules[component_type]
            self.draw_guide = _mod.ComponentGuide.draw_guide
            self.component_type = _mod.ComponentGuide.componentType
            self.comp_guide = self.get_componentGuide(self.component_type)
            orig_modal_positions = self.comp_guide.modalPositions
            if hasattr(_mod.ComponentGuide, "override_modalPositions"):
                if _mod.ComponentGuide.override_modalPositions is True:
                    self.comp_guide.modalPositions = (
                        _mod.ComponentGuide.custom_modalPositions.__get__(
                            self.comp_guide
                        )
                    )
                else:
                    self.comp_guide.modalPositions = orig_modal_positions
            else:
                self.comp_guide.modalPositions = orig_modal_positions
        else:
            raise exception.ComponentNotFoundError(
                f"Not found comp type. : {component_type}"
            )

    def create_guide(self, name, side, parent_root, idx=None, **opt):
        if self.comp_guide is None:
            return None
        parent_root = self.vaildate_guide(parent_root)
        if not parent_root:
            return None
        if not idx:
            idx = 0

        guide_names = self.draw_guide(
            name,
            self.comp_guide,
            side,
            idx,
            parent_root,
            **opt,
        )
        return guide_names
