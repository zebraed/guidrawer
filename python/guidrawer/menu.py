#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import pymel.core as pm

import mgear.menu

from . import ui


def mGear_add_menu():
    menuId = mgear.menu.menuId
    pm.setParent(menuId, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="Guidrawer", command=ui.show)
