#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import os
import importlib
from collections import OrderedDict

from . import exception
from . import compat


COMPONENT_PATH = os.path.join(os.path.abspath((os.path.dirname(__file__))),
                              "component")


class Loader(object):
    """
    draw component loader class
    """
    def __init__(self):
        self.__mods_dict = OrderedDict()
        self.is_loaded = False

    def load_component(self, comp_path=None):
        _mods = dict()
        if not comp_path:
            comp_path = COMPONENT_PATH

        for i_file in os.listdir(comp_path):
            if os.path.isfile(os.path.join(comp_path, i_file)):
                if i_file.endswith(".py"):
                    file = os.path.splitext(os.path.basename(i_file))[0]
                    if file == "__init__":
                        continue
                    try:
                        mod = importlib.import_module("guidrawer.component." + file)
                        compat.reload(mod)
                    except exception.ComponentImportError:
                        print("Can not import component module.")
                    else:
                        _mods[file] = mod
        if len(_mods):
            self.is_loaded = True

        self.__mods_dict = OrderedDict(sorted(list(_mods.items()),
                            key=lambda x: x[1].ComponentGuide.order,
                            reverse=False))

        return self.__mods_dict

    def list_component_name(self):
        if len(self.__mods_dict):
            return [name for name in list(self.__mods_dict.keys())]
        else:
            raise exception.NotLoadedError("Not loaded component.")

    def search_component(self, mod_name):
        pass
