#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
for Multiple Drawing the mGear's Guide Component.
"""
import os

from PySide2 import QtCore, QtWidgets

from maya import cmds
from pymel import core as pm

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from . import const
from . import decorator
from . import drawer
from . import model
from . import widget


class GuidrawerUI(MayaQWidgetBaseMixin, QtWidgets.QMainWindow):
    title = "Guidrawer"
    windowName = "guidrawer_widget"

    def __init__(self, parent=None):
        super(GuidrawerUI, self).__init__(parent)
        if cmds.window(self.windowName, q=True, ex=True):
            cmds.deleteUI(self.windowName)
        self.setObjectName(self.windowName)
        self.setWindowTitle(self.title)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips)

        self.__gd = drawer.Guidrawer()
        self.__core = model.Core()

        self.__main_widget = None
        self.__comp_cmb_widget = None
        self.__base_name_le_wiget = None
        self.__side_cmb_widget = None
        self.__idx_spin_widget = None
        self.__parentRoot_le_widget = None
        self.__chain_initializer_widget = None
        self.__sec_num_spin_widget = None
        self.__dir_axis_cmb_widget = None
        self.__spacing_float_widget = None

        self.__create_gd_btn = None
        self.__mir_gd_btn = None
        self.__dup_gd_btn = None

        self.__initialize()

        self.name = None
        self.current_side = None
        self.current_compType = None
        self.axis_dir = None
        self.axis_idx = None

        setting_file = os.path.join(os.getenv("MAYA_APP_DIR"),
                                    self.windowName + "_windowPref.ini")
        self.pyside_setting = QtCore.QSettings(setting_file,
                                               QtCore.QSettings.IniFormat)
        self.pyside_setting.setIniCodec("utf-8")

    def __initialize(self):
        self.__main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.__main_widget)

        opt_widget = QtWidgets.QWidget(parent=self.__main_widget)
        main_option_layout = QtWidgets.QVBoxLayout(opt_widget)
        main_option_layout.setContentsMargins(0, 0, 0, 0)

        contents_widget = QtWidgets.QWidget(parent=self.__main_widget)
        contents_layout = QtWidgets.QVBoxLayout(contents_widget)

        comp_layout = QtWidgets.QHBoxLayout()
        main_option_layout.addLayout(comp_layout, 0)

        opt_layout = QtWidgets.QHBoxLayout()
        parentRoot_layout = QtWidgets.QHBoxLayout()

        self.__chain_initializer_widget = c_wdt = QtWidgets.QFrame(self)
        self.__chain_initializer_widget.hide()
        self.chain_opt_layout = chain_opt_layout = QtWidgets.QVBoxLayout()
        chain_opt_sub_layout = QtWidgets.QHBoxLayout()
        chain_opt_sub_layout2 = QtWidgets.QHBoxLayout()
        chain_opt_layout.addLayout(chain_opt_sub_layout)
        chain_opt_layout.addLayout(chain_opt_sub_layout2)

        self.__chain_initializer_widget.setLayout(chain_opt_layout)

        main_option_layout.addLayout(opt_layout, 1)
        main_option_layout.addLayout(parentRoot_layout, 2)

        # side label combo box
        self.__comp_cmb_widget = widget.ComboBox(self.__core.comp_model(),
                                                 parent=opt_widget)
        cmps = self.__gd.list_component_name()
        self.__comp_cmb_widget.setItems(cmps)
        self.load_guide()

        # ------ 2nd section ----- #
        # base name line edit
        self.__base_name_le_wiget = QtWidgets.QLineEdit(parent=opt_widget)
        self.__base_name_le_wiget.setPlaceholderText("Set Base Name...")

        # side label combo box
        self.__side_cmb_widget = widget.ComboBox(self.__core.side_model(),
                                                 parent=opt_widget)
        _sides = const.VALID_SIDE_INDEX_LIST
        self.__side_cmb_widget.setItems(_sides)

        # ldx spin box
        self.__idx_spin_widget = QtWidgets.QSpinBox(parent=opt_widget)

        # parent root line edit
        self.__parentRoot_le_widget = widget.TextFieldButton(
            button_label_text="set", parent=opt_widget)
        self.__parentRoot_le_widget.button.clicked.connect(lambda x:
            self.__set_parent_root(cmds.ls(sl=True, fl=True)[0]))
        self.__parentRoot_le_widget.setPlaceholderText("Set Parent Guide...")

        # ------ 3rd section ----- #
        # for chain type opt widget
        #self.__chain_label = QtWidgets.QLabel("Chain Initializer", self)

        self.__sec_num_spin_widget = QtWidgets.QSpinBox(parent=c_wdt)
        self.__sec_num_spin_widget.setMinimum(3)
        self.__sec_num_spin_widget.setPrefix("Sections Number:")

        self.__dir_axis_cmb_widget = widget.ComboBox(self.__core.axis_dir_model(),
                                                     parent=c_wdt)
        _axies = const.VALID_AXIS_INDEX_DICT
        self.__dir_axis_cmb_widget.setItems(_axies)

        self.__spacing_label = QtWidgets.QLabel("Spacing:", self)
        self.__spacing_float_widget = widget.FloatSlider(parent=c_wdt)
        self.__spacing_float_widget.setRange(0.0001, 20.0000)
        self.__spacing_float_widget.setValue(1)

        self.__hl_frame1 = widget.HorizontalLine(self)

        comp_layout.addWidget(self.__comp_cmb_widget)
        opt_layout.addWidget(self.__base_name_le_wiget)
        opt_layout.addWidget(self.__side_cmb_widget)
        opt_layout.addWidget(self.__idx_spin_widget)
        parentRoot_layout.addWidget(self.__parentRoot_le_widget.button)
        parentRoot_layout.addWidget(self.__parentRoot_le_widget)

        chain_opt_sub_layout.addWidget(self.__sec_num_spin_widget)
        chain_opt_sub_layout.addWidget(self.__dir_axis_cmb_widget)
        chain_opt_sub_layout2.addWidget(self.__spacing_label)
        chain_opt_sub_layout2.addWidget(self.__spacing_float_widget)

        main_option_layout.addWidget(self.__chain_initializer_widget)
        main_option_layout.addWidget(self.__hl_frame1)

        button_layout = QtWidgets.QVBoxLayout()
        self.__create_gd_btn = QtWidgets.QPushButton("Create Guide")
        self.__create_gd_btn.clicked.connect(lambda x:
            self.create_guide_pos(cmds.ls(os=True, fl=True)))
        button_layout.addWidget(self.__create_gd_btn)

        self.__mir_gd_btn = QtWidgets.QPushButton("Mirror Guide")
        self.__mir_gd_btn.clicked.connect(lambda x:
            self.__gd.duplicate_guide(cmds.ls(sl=True, fl=True),
                                      symmetrize=True))
        button_layout.addWidget(self.__mir_gd_btn)

        self.__dup_gd_btn = QtWidgets.QPushButton("Duplicate Guide")
        self.__dup_gd_btn.clicked.connect(lambda x:
            self.__gd.duplicate_guide(cmds.ls(sl=True, fl=True),
                                      symmetrize=False))
        button_layout.addWidget(self.__dup_gd_btn)

        self.__hl_frame2 = widget.HorizontalLine(self)

        central_layout = QtWidgets.QVBoxLayout(self.__main_widget)
        central_layout.setAlignment(QtCore.Qt.AlignTop)
        central_layout.setContentsMargins(10, 10, 10, 10)
        central_layout.setSpacing(5)
        central_layout.addWidget(opt_widget, 0)
        central_layout.addWidget(contents_widget, 1)
        central_layout.addWidget(self.__hl_frame2, 2)

        contents_layout.addLayout(button_layout)

        self.__core.sideChanged.connect(self.__on_side_changed)
        self.__core.compTypeChanged.connect(self.__on_comp_type_changed)
        self.__core.axisDirChanged.connect(self.__on_axis_dir_changed)

    def __on_side_changed(self, side):
        self.current_side = side

    def __on_comp_type_changed(self, compType):
        self.current_compType = compType
        self.load_guide()
        self.__chain_widget_switch()

    def __on_axis_dir_changed(self, axis_dir):
        self.axis_dir = axis_dir
        self.axis_idx = self.__core.axis_dir_model().idxFromItem(axis_dir)

    def __chain_widget_switch(self):
        if self.__core.isChain(self.current_compType):
            self.__chain_initializer_widget.show()
        else:
            self.__chain_initializer_widget.hide()
            QtCore.QTimer.singleShot(0, self.shrink)

    def __set_name(self):
        self.name = self.__get_base_name()

    def __set_parent_root(self, node=None):
        self.__parentRoot_le_widget.setText(node)

    def __get_base_name(self):
        return self.__base_name_le_wiget.text()

    def __get_side(self):
        return self.__side_cmb_widget.currentText()

    def __get_idx(self):
        return self.__idx_spin_widget.value()

    def __get_parent_root(self):
        return self.__parentRoot_le_widget.text()

    def __get_comp_type(self):
        return self.__comp_cmb_widget.currentText()

    def __get_section_num(self):
        return self.__sec_num_spin_widget.value()

    def __get_dir_axis(self):
        return self.__dir_axis_cmb_widget.currentText()

    def __get_dir_axis_idx(self):
        return self.__core.axis_dir_model().idxFromItem(self.__get_dir_axis())

    def __get_spacing_num(self):
        return self.__spacing_float_widget.value()

    def shrink(self):
        self.resize(QtCore.QSize())
        self.adjustSize()

    def show(self):
        self.restore()
        self.shrink()
        super(GuidrawerUI, self).show()

    def restore(self):
        if self.pyside_setting:
            self.restoreGeometry(self.pyside_setting.value(
                                 self.windowName + "-geom"))

    def closeEvent(self, event):
        if self.pyside_setting:
            self.pyside_setting.setValue(self.windowName + "-geom",
                                         self.saveGeometry())

    def get_chain_opt(self):
        if self.__core.isChain(self.__get_comp_type()):
            chain_opt = {"sections_number": self.__get_section_num(),
                         "dir_axis": self.__get_dir_axis_idx(),
                         "spacing": self.__get_spacing_num()
                         }
        else:
            chain_opt = {}
        return chain_opt

    def load_guide(self):
        self.__gd.load_component(componentType=self.__get_comp_type())

    def create_guide(self):
        self.__set_name()
        chain_opt = self.get_chain_opt()
        self.load_guide()
        guide_name = self.__gd.create_guide(name=self.name,
                                            side=self.__get_side(),
                                            idx=self.__get_idx(),
                                            parentRoot=self.__get_parent_root(),
                                            **chain_opt)
        return guide_name

    @decorator.undo
    def create_guide_pos(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for i_node in nodes:
            guide_name = self.create_guide()
            pos = pm.xform(i_node, q=True, t=True, ws=True)
            pm.xform(guide_name, t=pos, ws=True)


def show(*args):
    a = GuidrawerUI()
    a.show()
