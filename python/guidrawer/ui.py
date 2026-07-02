"""Multiple Drawing the mGear's Guide Component."""
import os

from mgear.vendor.Qt import QtCore, QtWidgets
from maya import cmds
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
        super().__init__(parent)
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

        self.__idx_updating = False

        self.__initialize()

        self.name = None
        self.current_side = None
        self.current_compType = None
        self.axis_dir = None
        self.axis_idx = None

        setting_file = os.path.join(
            os.getenv("MAYA_APP_DIR"),
            f"{self.windowName}_windowPref.ini",
        )
        self.pyside_setting = QtCore.QSettings(
            setting_file, QtCore.QSettings.IniFormat
        )
        if hasattr(self.pyside_setting, "setIniCodec"):
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
        chain_opt_layout = QtWidgets.QVBoxLayout()
        chain_opt_sub_layout = QtWidgets.QHBoxLayout()
        chain_opt_sub_layout2 = QtWidgets.QHBoxLayout()
        chain_opt_layout.addLayout(chain_opt_sub_layout)
        chain_opt_layout.addLayout(chain_opt_sub_layout2)

        self.__chain_initializer_widget.setLayout(chain_opt_layout)

        main_option_layout.addLayout(opt_layout, 1)
        main_option_layout.addLayout(parentRoot_layout, 2)

        self.__comp_cmb_widget = widget.ComboBox(
            self.__core.comp_model(), parent=opt_widget
        )
        cmps = self.__gd.list_component_name()
        self.__comp_cmb_widget.setItems(cmps)

        self.__base_name_le_wiget = QtWidgets.QLineEdit(parent=opt_widget)
        self.__base_name_le_wiget.setPlaceholderText("Set Base Name...")

        self.__side_cmb_widget = widget.ComboBox(
            self.__core.side_model(), parent=opt_widget
        )
        _sides = const.VALID_SIDE_INDEX_LIST
        self.__side_cmb_widget.setItems(_sides)

        self.__idx_spin_widget = QtWidgets.QSpinBox(parent=opt_widget)
        self.__idx_spin_widget.setMinimum(0)
        self.__idx_spin_widget.valueChanged.connect(self.__on_idx_changed)

        self.__base_name_le_wiget.textChanged.connect(
            self.__refresh_component_index
        )

        self.__parentRoot_le_widget = widget.TextFieldButton(
            button_label_text="set", parent=opt_widget
        )
        self.__parentRoot_le_widget.editingFinished.connect(
            self.__refresh_component_index
        )
        self.__parentRoot_le_widget.button.clicked.connect(
            lambda x: self.__set_parent_root(cmds.ls(sl=True, fl=True)[0])
        )
        self.__parentRoot_le_widget.setPlaceholderText("Set Parent Guide...")

        self.__sec_num_spin_widget = QtWidgets.QSpinBox(parent=c_wdt)
        self.__sec_num_spin_widget.setMinimum(3)
        self.__sec_num_spin_widget.setPrefix("Sections Number:")

        self.__dir_axis_cmb_widget = widget.ComboBox(
            self.__core.axis_dir_model(), parent=c_wdt
        )
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
        self.__create_gd_btn.clicked.connect(
            lambda x: self.create_guide_pos(cmds.ls(sl=True, fl=True))
        )
        button_layout.addWidget(self.__create_gd_btn)

        self.__mir_gd_btn = QtWidgets.QPushButton("Mirror Guide")
        self.__mir_gd_btn.clicked.connect(
            lambda x: self.__duplicate_guide(symmetrize=True)
        )
        button_layout.addWidget(self.__mir_gd_btn)

        self.__dup_gd_btn = QtWidgets.QPushButton("Duplicate Guide")
        self.__dup_gd_btn.clicked.connect(
            lambda x: self.__duplicate_guide(symmetrize=False)
        )
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

        # Update chain option visibility for the initially selected component
        self.current_compType = self.__get_comp_type()
        self.__chain_widget_switch()
        self.__refresh_component_index()

    def __on_side_changed(self, side):
        self.current_side = side
        self.__refresh_component_index()

    def __on_comp_type_changed(self, comp_type):
        self.current_compType = comp_type
        self.__chain_widget_switch()
        self.__refresh_component_index()

    def __on_axis_dir_changed(self, axis_dir):
        self.axis_dir = axis_dir
        self.axis_idx = self.__core.axis_dir_model().idxFromItem(axis_dir)

    def __chain_widget_switch(self):
        if self.__gd.is_chain(self.current_compType):
            self.__chain_initializer_widget.show()
        else:
            self.__chain_initializer_widget.hide()
            QtCore.QTimer.singleShot(0, self.shrink)

    def __set_name(self):
        self.name = self.__get_base_name()

    def __set_parent_root(self, node=None):
        self.__parentRoot_le_widget.setText(node)
        self.__refresh_component_index()

    def __set_idx(self, value):
        self.__idx_updating = True
        self.__idx_spin_widget.blockSignals(True)
        self.__idx_spin_widget.setValue(value)
        self.__idx_spin_widget.blockSignals(False)
        self.__idx_updating = False

    def __refresh_component_index(self):
        next_idx = self.__gd.get_next_component_index(
            comp_type=self.__get_comp_type(),
            name=self.__get_base_name(),
            side=self.__get_side(),
            parent_root=self.__get_parent_root(),
        )
        self.__set_idx(next_idx)

    def __on_idx_changed(self, value):
        if self.__idx_updating:
            return
        # mGear component settings: updateProperties -> rename -> setIndex,
        # then sync spinbox from comp_index on the guide root
        valid_idx = self.__gd.get_next_component_index(
            comp_type=self.__get_comp_type(),
            name=self.__get_base_name(),
            side=self.__get_side(),
            parent_root=self.__get_parent_root(),
            start_index=value,
        )
        if valid_idx != value:
            self.__set_idx(valid_idx)

    def __sync_idx_from_created_guide(self, guide_root):
        if not guide_root or not cmds.objExists(f"{guide_root}.comp_index"):
            return
        next_idx = self.__gd.get_next_component_index(
            comp_type=self.__get_comp_type(),
            name=self.__get_base_name(),
            side=self.__get_side(),
            parent_root=self.__get_parent_root(),
        )
        self.__set_idx(next_idx)

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
        self.__refresh_component_index()
        self.shrink()
        super().show()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowActivate:
            self.__refresh_component_index()

    def restore(self):
        if self.pyside_setting:
            self.restoreGeometry(
                self.pyside_setting.value(f"{self.windowName}-geom")
            )

    def closeEvent(self, event):
        if self.pyside_setting:
            self.pyside_setting.setValue(
                f"{self.windowName}-geom", self.saveGeometry()
            )

    def get_chain_opt(self):
        if self.__gd.is_chain(self.__get_comp_type()):
            chain_opt = {
                "sections_number": self.__get_section_num(),
                "dir_axis": self.__get_dir_axis_idx(),
                "spacing": self.__get_spacing_num(),
            }
        else:
            chain_opt = {}
        return chain_opt

    def create_guide(self):
        self.__set_name()
        chain_opt = self.get_chain_opt()
        guide_name = self.__gd.create_guide(
            comp_type=self.__get_comp_type(),
            name=self.name,
            side=self.__get_side(),
            idx=self.__get_idx(),
            parent_root=self.__get_parent_root(),
            **chain_opt,
        )
        self.__sync_idx_from_created_guide(guide_name)
        return guide_name

    @decorator.undo
    def create_guide_pos(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for i_node in nodes:
            guide_name = self.create_guide()
            if not guide_name:
                return
            pos = cmds.xform(i_node, q=True, t=True, ws=True)
            cmds.xform(guide_name, t=pos, ws=True)

    def __duplicate_guide(self, symmetrize=False):
        self.__gd.duplicate_guide(cmds.ls(sl=True, fl=True), symmetrize)
        self.__refresh_component_index()


def show(*args):
    a = GuidrawerUI()
    a.show()
