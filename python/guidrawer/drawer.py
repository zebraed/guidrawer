#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from . import base
from . import exception
from . import loader


class Guidrawer(base.GuidrawerBase):
    """
    Draw main class.
    """
    def __init__(self):
        super(Guidrawer, self).__init__()
        self.__loader = loader.Loader()
        self.modules = None
        self.component_type = None
        self.comp_guide = None
        self.reload_module()

    def reload_module(self):
        self.modules = self.__loader.load_component()

    def list_component_name(self):
        return [name for name in list(self.modules.keys())]

    def load_component(self, componentType):
        if componentType in self.modules:
            _mod = self.modules[componentType]
            self.draw_guide = _mod.ComponentGuide.draw_guide
            self.component_type = _mod.ComponentGuide.componentType
            self.comp_guide = self.get_componentGuide(self.component_type)
            orig_modalPositions = self.comp_guide.modalPositions
            if hasattr(_mod.ComponentGuide, "override_modalPositions"):
                if _mod.ComponentGuide.override_modalPositions is True:
                    self.comp_guide.modalPositions = _mod.ComponentGuide.custom_modalPositions.__get__(self.comp_guide)
                else:
                    self.comp_guide.modalPositions = orig_modalPositions
            else:
                self.comp_guide.modalPositions = orig_modalPositions
        else:
            raise exception.ComponentNotFoundError("Not found comp type. : {}".format(componentType))

    def create_guide(self, name, side, parentRoot, idx=None, **opt):
        if self.comp_guide is None:
            return
        parentRoot = self.vaildate_guide(parentRoot)
        if not parentRoot:
            return
        if not idx:
            idx = 0

        guide_names = self.draw_guide(name,
                                      self.comp_guide,
                                      side,
                                      idx,
                                      parentRoot,
                                      **opt)
        return guide_names
