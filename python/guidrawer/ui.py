"""Multiple Drawing the mGear's Guide Component."""
import os

from maya import cmds

from mgear.vendor.Qt import QtCore, QtGui, QtWidgets

from . import const
from . import decorator
from . import drawer
from . import maya_util
from . import model
from . import shifter_bridge as bridge
from . import widget


ICON_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    "icons",
    "guidrawer_icon.svg",
)

_SOLO_MOVE_ON_STYLE = "QPushButton { border: 2px solid #FFD700; }"


class GuidrawerUI(QtWidgets.QMainWindow):
    """
    Guidrawer UI class
    """
    title = "Guidrawer"
    object_name = "guidrawer_widget"

    def __init__(self, parent=None):
        if parent is None:
            parent = maya_util.get_maya_main_window()
        super().__init__(parent)

        self._close_other_instances()

        self.setObjectName(self.object_name)
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
        self.__parent_root_le_widget = None
        self.__pre_settings_btn = None
        self.__reset_pre_settings_btn = None
        self.__create_gd_btn = None
        self.__settings_btn = None
        self.__mir_gd_btn = None
        self.__dup_gd_btn = None
        self.__extr_ctrl_btn = None
        self.__del_gd_btn = None
        self.__del_keep_child_gd_btn = None
        self.__vanilla_build_btn = None
        self.__full_build_btn = None
        self.__fit_to_pos_btn = None
        self.__align_mid_pos_btn = None
        self.__fit_nearest_btn = None
        self.__align_rot_btn = None
        self.__align_mid_rot_btn = None
        self.__align_rot_nearest_btn = None
        self.__aim_x_btn = None
        self.__aim_y_btn = None
        self.__aim_z_btn = None
        self.__rot_x90_btn = None
        self.__rot_y90_btn = None
        self.__rot_z90_btn = None
        self.__solo_move_btn = None

        self.__solo_move_size_locked = False

        self.__idx_updating = False

        self._set_window_icon()

        setting_file = os.path.join(
            os.getenv("MAYA_APP_DIR"),
            f"{self.object_name}_windowPref.ini",
        )
        self.pyside_setting = QtCore.QSettings(
            setting_file, QtCore.QSettings.IniFormat
        )
        if hasattr(self.pyside_setting, "setIniCodec"):
            self.pyside_setting.setIniCodec("utf-8")

        self.__initialize()
        self._setup_focus_clear()

        self.name = None
        self.current_side = None
        self.current_comp_type = None

    def _close_other_instances(self):
        """
        Close other instances of the GuidrawerUI.
        """
        singleton_key = self.object_name
        for q_window in self.parent().findChildren(QtWidgets.QMainWindow):
            if q_window is self:
                continue
            if q_window.objectName() == singleton_key:
                q_window.close()

    def _set_window_icon(self) -> None:
        if os.path.isfile(ICON_PATH):
            icon = QtGui.QIcon(ICON_PATH)
            if not icon.isNull():
                self.setWindowIcon(icon)

    def __comp_type_setting_key(self):
        return f"{self.object_name}-comp_type"

    def __save_comp_type(self, comp_type):
        if self.pyside_setting and comp_type:
            self.pyside_setting.setValue(
                self.__comp_type_setting_key(), comp_type
            )

    def __restore_comp_type(self):
        if not self.pyside_setting:
            return

        saved = self.pyside_setting.value(self.__comp_type_setting_key())
        if not saved:
            return

        items = self.__core.comp_model().items()
        if saved not in items:
            return

        self.__comp_cmb_widget.setCurrentIndex(items.index(saved))

    def __initialize(self):
        self.__main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.__main_widget)

        opt_widget = QtWidgets.QWidget(parent=self.__main_widget)
        main_option_layout = QtWidgets.QVBoxLayout(opt_widget)
        main_option_layout.setContentsMargins(0, 0, 0, 0)
        main_option_layout.setAlignment(QtCore.Qt.AlignTop)

        comp_layout = QtWidgets.QHBoxLayout()
        main_option_layout.addLayout(comp_layout)

        opt_layout = QtWidgets.QHBoxLayout()
        parentRoot_layout = QtWidgets.QHBoxLayout()

        self.__comp_cmb_widget = widget.ComboBox(
            self.__core.comp_model(), parent=opt_widget
        )
        cmps = self.__gd.list_component_name()
        self.__comp_cmb_widget.setItems(cmps)
        self.__comp_cmb_widget.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.__comp_cmb_widget.setMinimumContentsLength(1)
        self.__comp_cmb_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.__comp_cmb_widget.currentIndexChanged.connect(
            self.__update_pre_settings_btn
        )
        self.__restore_comp_type()

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

        self.__parent_root_le_widget = widget.TextFieldButton(parent=opt_widget)
        self.__parent_root_le_widget.button.setText("")
        self.__parent_root_le_widget.button.setIcon(
            QtGui.QIcon(":/dopeSheetSelect.png")
        )
        self.__parent_root_le_widget.editingFinished.connect(
            self.__refresh_component_index
        )
        self.__parent_root_le_widget.button.clicked.connect(
            lambda x: self.__set_parent_root_from_selection()
        )
        self.__parent_root_le_widget.setPlaceholderText("Set Parent Guide...")

        self.__pre_settings_btn = QtWidgets.QPushButton("", parent=opt_widget)
        self.__pre_settings_btn.setIcon(QtGui.QIcon(":/RS_settings_pop.png"))
        self.__pre_settings_btn.setToolTip("Pre Settings...")
        self.__pre_settings_btn.clicked.connect(
            lambda x: self.__open_pre_settings()
        )

        self.__reset_pre_settings_btn = QtWidgets.QPushButton("", parent=opt_widget)
        self.__reset_pre_settings_btn.setIcon(QtGui.QIcon(":/deletePreset.png"))
        self.__reset_pre_settings_btn.setToolTip("Reset Settings")
        self.__reset_pre_settings_btn.clicked.connect(
            lambda x: self.__reset_pre_settings()
        )

        self.__hl_frame1 = widget.HorizontalLine(self)

        comp_layout.addWidget(self.__comp_cmb_widget, 1)
        comp_layout.addWidget(self.__pre_settings_btn)
        comp_layout.addWidget(self.__reset_pre_settings_btn)
        opt_layout.addWidget(self.__base_name_le_wiget)
        opt_layout.addWidget(self.__side_cmb_widget)
        opt_layout.addWidget(self.__idx_spin_widget)
        parentRoot_layout.addWidget(self.__parent_root_le_widget.button)
        parentRoot_layout.addWidget(self.__parent_root_le_widget, 1)

        main_option_layout.addLayout(opt_layout)
        main_option_layout.addLayout(parentRoot_layout)

        self.__create_gd_btn = QtWidgets.QPushButton("Draw", parent=opt_widget)
        self.__create_gd_btn.setIcon(QtGui.QIcon(":/createBin.png"))
        self.__create_gd_btn.clicked.connect(
            lambda x: self.create_guide_pos(cmds.ls(sl=True, fl=True))
        )

        self.__settings_btn = QtWidgets.QPushButton("Settings", parent=opt_widget)
        self.__settings_btn.setIcon(QtGui.QIcon(":/advancedSettings.png"))
        self.__settings_btn.clicked.connect(
            lambda x: self.__open_settings()
        )

        main_option_layout.addWidget(self.__create_gd_btn)
        main_option_layout.addWidget(self.__settings_btn)
        main_option_layout.addWidget(self.__hl_frame1)

        tools_group, tools_frame = widget.group_box_frame(
            "Guide Tools", self.__main_widget, "guideTools"
        )
        tools_group.toggled.connect(self.__on_collapsible_group_toggled)
        tools_inner_layout = QtWidgets.QVBoxLayout(tools_frame)
        tools_inner_layout.setSpacing(0)
        tools_inner_layout.setContentsMargins(0, 0, 0, 0)

        button_layout = QtWidgets.QGridLayout()
        button_layout.setSizeConstraint(
            QtWidgets.QLayout.SetFixedSize
        )
        self.__dup_gd_btn = QtWidgets.QPushButton("Duplicate")
        self.__dup_gd_btn.setIcon(QtGui.QIcon(":/teCompDup.png"))
        self.__dup_gd_btn.clicked.connect(
            lambda x: self.__duplicate_guide(symmetrize=False)
        )
        button_layout.addWidget(self.__dup_gd_btn, 0, 0)

        self.__mir_gd_btn = QtWidgets.QPushButton("Mirror")
        self.__mir_gd_btn.setIcon(QtGui.QIcon(":/polySymmetrizeUV.png"))
        self.__mir_gd_btn.clicked.connect(
            lambda x: self.__duplicate_guide(symmetrize=True)
        )
        button_layout.addWidget(self.__mir_gd_btn, 0, 1)

        self.__extr_ctrl_btn = QtWidgets.QPushButton("Extr. Ctrl")
        self.__extr_ctrl_btn.setIcon(QtGui.QIcon(":/extend.png"))
        self.__extr_ctrl_btn.clicked.connect(
            lambda x: self.__extract_controls()
        )
        button_layout.addWidget(self.__extr_ctrl_btn, 0, 2)

        for col in range(3):
            button_layout.setColumnStretch(col, 1)

        self.__del_gd_btn = QtWidgets.QPushButton("Delete")
        self.__del_gd_btn.setIcon(QtGui.QIcon(":/deleteRenderPass.png"))
        self.__del_gd_btn.clicked.connect(
            lambda x: self.__delete_guide()
        )

        self.__del_keep_child_gd_btn = QtWidgets.QPushButton("Delete Keep Child")
        self.__del_keep_child_gd_btn.setIcon(
            QtGui.QIcon(":/deletePCM.png")
        )
        self.__del_keep_child_gd_btn.clicked.connect(
            lambda x: self.__delete_guide_keep_children()
        )

        delete_layout = QtWidgets.QHBoxLayout()
        delete_layout.addWidget(self.__del_gd_btn)
        delete_layout.addWidget(self.__del_keep_child_gd_btn)

        self.__hl_frame3 = widget.HorizontalLine(tools_frame)

        self.__vanilla_build_btn = QtWidgets.QPushButton("Vanilla Build")
        self.__vanilla_build_btn.setIcon(QtGui.QIcon(":/HIKcreateCustRig.png"))
        self.__vanilla_build_btn.clicked.connect(
            lambda x: self.__vanilla_build_guide()
        )

        self.__full_build_btn = QtWidgets.QPushButton("Full Build")
        self.__full_build_btn.setIcon(QtGui.QIcon(":/HIKcreateControlRig.png"))
        self.__full_build_btn.clicked.connect(
            lambda x: self.__full_build_guide()
        )

        build_layout = QtWidgets.QHBoxLayout()
        build_layout.setContentsMargins(0, 0, 0, 0)
        build_layout.addWidget(self.__vanilla_build_btn)
        build_layout.addWidget(self.__full_build_btn)

        tools_inner_layout.addLayout(button_layout)
        tools_inner_layout.addLayout(delete_layout)
        tools_inner_layout.addWidget(self.__hl_frame3)
        tools_inner_layout.addLayout(build_layout)

        align_group, align_frame = widget.group_box_frame(
            "Placement Tools", self.__main_widget, "guideAlign"
        )
        align_group.toggled.connect(self.__on_collapsible_group_toggled)
        align_inner_layout = QtWidgets.QVBoxLayout(align_frame)
        align_inner_layout.setSpacing(0)
        align_inner_layout.setContentsMargins(0, 0, 0, 0)

        align_layout = QtWidgets.QGridLayout()
        align_layout.setSizeConstraint(
            QtWidgets.QLayout.SetFixedSize
        )

        self.__fit_to_pos_btn = QtWidgets.QPushButton("Fit to Pos")
        self.__fit_to_pos_btn.setIcon(QtGui.QIcon(":/pivotPos.png"))
        self.__fit_to_pos_btn.clicked.connect(
            lambda x: self.__fit_to_pos()
        )
        align_layout.addWidget(self.__fit_to_pos_btn, 0, 0)

        self.__align_mid_pos_btn = QtWidgets.QPushButton("Mid Pos")
        self.__align_mid_pos_btn.setIcon(QtGui.QIcon(":/UVAlignMiddleV.png"))
        self.__align_mid_pos_btn.clicked.connect(
            lambda x: self.__align_mid_pos()
        )
        align_layout.addWidget(self.__align_mid_pos_btn, 0, 1)

        self.__fit_nearest_btn = QtWidgets.QPushButton("Fit Nearest")
        self.__fit_nearest_btn.setIcon(QtGui.QIcon(":/pivotResetPos.png"))
        self.__fit_nearest_btn.clicked.connect(
            lambda x: self.__fit_nearest()
        )
        align_layout.addWidget(self.__fit_nearest_btn, 0, 2)

        self.__align_rot_btn = QtWidgets.QPushButton("Align Rot")
        self.__align_rot_btn.setIcon(QtGui.QIcon(":/pivotAlign.png"))
        self.__align_rot_btn.clicked.connect(
            lambda x: self.__align_rot()
        )
        align_layout.addWidget(self.__align_rot_btn, 1, 0)

        self.__align_mid_rot_btn = QtWidgets.QPushButton("Mid Rot")
        self.__align_mid_rot_btn.setIcon(QtGui.QIcon(":/polyAlignUVLinear.png"))
        self.__align_mid_rot_btn.clicked.connect(
            lambda x: self.__align_mid_rot()
        )
        align_layout.addWidget(self.__align_mid_rot_btn, 1, 1)

        self.__align_rot_nearest_btn = QtWidgets.QPushButton("Rot Nearest")
        self.__align_rot_nearest_btn.setIcon(QtGui.QIcon(":/pivotResetOri.png"))
        self.__align_rot_nearest_btn.clicked.connect(
            lambda x: self.__align_rot_nearest()
        )
        align_layout.addWidget(self.__align_rot_nearest_btn, 1, 2)

        aim_icon = QtGui.QIcon(":/poleVectorConstraint.png")

        self.__aim_x_btn = QtWidgets.QPushButton("Aim X")
        self.__aim_x_btn.setIcon(aim_icon)
        self.__aim_x_btn.clicked.connect(
            lambda x: self.__aim_x()
        )
        align_layout.addWidget(self.__aim_x_btn, 2, 0)

        self.__aim_y_btn = QtWidgets.QPushButton("Aim Y")
        self.__aim_y_btn.setIcon(aim_icon)
        self.__aim_y_btn.clicked.connect(
            lambda x: self.__aim_y()
        )
        align_layout.addWidget(self.__aim_y_btn, 2, 1)

        self.__aim_z_btn = QtWidgets.QPushButton("Aim Z")
        self.__aim_z_btn.setIcon(aim_icon)
        self.__aim_z_btn.clicked.connect(
            lambda x: self.__aim_z()
        )
        align_layout.addWidget(self.__aim_z_btn, 2, 2)

        rotate_icon = QtGui.QIcon(":/rotate_M.png")

        self.__rot_x90_btn = QtWidgets.QPushButton("X 90")
        self.__rot_x90_btn.setIcon(rotate_icon)
        self.__wire_rotate_button(self.__rot_x90_btn, "x")
        align_layout.addWidget(self.__rot_x90_btn, 3, 0)

        self.__rot_y90_btn = QtWidgets.QPushButton("Y 90")
        self.__rot_y90_btn.setIcon(rotate_icon)
        self.__wire_rotate_button(self.__rot_y90_btn, "y")
        align_layout.addWidget(self.__rot_y90_btn, 3, 1)

        self.__rot_z90_btn = QtWidgets.QPushButton("Z 90")
        self.__rot_z90_btn.setIcon(rotate_icon)
        self.__wire_rotate_button(self.__rot_z90_btn, "z")
        align_layout.addWidget(self.__rot_z90_btn, 3, 2)

        for col in range(3):
            align_layout.setColumnStretch(col, 1)

        align_inner_layout.addLayout(align_layout)

        solo_move_layout = QtWidgets.QHBoxLayout()
        solo_move_layout.setContentsMargins(0, 0, 0, 0)

        self.__solo_move_btn = QtWidgets.QPushButton("Solo Move")
        self.__solo_move_btn.setIcon(QtGui.QIcon(":/move_M.png"))
        self.__solo_move_btn.setCheckable(True)
        self.__solo_move_btn.toggled.connect(self.__on_solo_move_toggled)
        solo_move_layout.addWidget(self.__solo_move_btn)

        align_inner_layout.addLayout(solo_move_layout)

        central_layout = QtWidgets.QVBoxLayout(self.__main_widget)
        central_layout.setAlignment(QtCore.Qt.AlignTop)
        central_layout.setContentsMargins(10, 10, 10, 10)
        central_layout.setSpacing(5)
        central_layout.addWidget(opt_widget, 0)
        central_layout.addWidget(tools_group, 0)
        central_layout.addSpacing(8)
        central_layout.addWidget(align_group, 0)

        self.__core.sideChanged.connect(self.__on_side_changed)
        self.__core.compTypeChanged.connect(self.__on_comp_type_changed)

        self.current_comp_type = self.__get_comp_type()
        self.__refresh_component_index()
        self.__sync_solo_move_button()
        self.__update_pre_settings_btn()
        self.__update_full_build_btn()

    def __update_full_build_btn(self):
        if not self.__full_build_btn:
            return
        self.__full_build_btn.setEnabled(self.__gd.has_full_build_steps())

    def __update_pre_settings_btn(self):
        if not self.__pre_settings_btn:
            return
        has_settings = self.__gd.has_pre_settings(self.__get_comp_type())
        self.__pre_settings_btn.setEnabled(has_settings)
        if not self.__reset_pre_settings_btn:
            return
        has_cache = self.__gd.has_pre_settings_cache(self.__get_comp_type())
        self.__reset_pre_settings_btn.setEnabled(
            has_settings and has_cache
        )

    def __on_side_changed(self, side):
        self.current_side = side
        self.__refresh_component_index()

    def __on_comp_type_changed(self, comp_type):
        self.current_comp_type = comp_type
        self.__save_comp_type(comp_type)
        self.__refresh_component_index()
        self.__update_pre_settings_btn()

    def __set_name(self):
        self.name = self.__get_base_name()

    def __set_parent_root_from_selection(self):
        selection = cmds.ls(sl=True, fl=True)
        if not selection:
            cmds.warning("Nothing selected.")
            return
        self.__set_parent_root(selection[0])

    def __set_parent_root(self, node=None):
        if not node:
            cmds.warning("Nothing selected.")
            return

        validated = bridge.validate_guide(node)
        if not validated:
            return

        self.__parent_root_le_widget.setText(validated)
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
        return self.__parent_root_le_widget.text()

    def __get_comp_type(self):
        return self.__comp_cmb_widget.currentText()

    def shrink(self):
        central = self.centralWidget()
        if central and central.layout():
            central.layout().activate()
        self.adjustSize()
        width = self.width()
        if width <= 0:
            width = self.sizeHint().width()
        height = self.maximumHeight()
        if self.minimumHeight() == self.maximumHeight() and height > 0:
            self.resize(width, height)
            return
        self.resize(width, self.sizeHint().height())

    def __lock_window_height(self):
        width = self.width()
        if width <= 0:
            width = self.sizeHint().width()

        central = self.centralWidget()
        if central and central.layout():
            central.layout().activate()

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        height = self.sizeHint().height()
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.resize(width, height)

    def __on_collapsible_group_toggled(self, expanded):
        QtCore.QTimer.singleShot(0, self.__lock_window_height)

    def __finalize_window_layout(self):
        self.__lock_solo_move_button_size()
        self.__lock_window_height()

    def show(self):
        self.restore()
        self.__refresh_component_index()
        self.__sync_solo_move_button()
        self.__update_full_build_btn()
        self.shrink()
        super().show()
        QtCore.QTimer.singleShot(0, self.__finalize_window_layout)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowActivate:
            self.__refresh_component_index()
            self.__sync_solo_move_button()
            self.__update_pre_settings_btn()
            self.__update_full_build_btn()

    def restore(self):
        if self.pyside_setting:
            self.restoreGeometry(
                self.pyside_setting.value(f"{self.object_name}-geom")
            )

    def closeEvent(self, event):
        if self.pyside_setting:
            self.__save_comp_type(self.__get_comp_type())
            self.pyside_setting.setValue(
                f"{self.object_name}-geom", self.saveGeometry()
            )
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if (
            event.type() == QtCore.QEvent.MouseButtonPress
            and event.button() == QtCore.Qt.LeftButton
            and obj is not self
            and not self._is_inside_input_widget(obj)
        ):
            self._clear_input_focus()

        if obj is self.parent() and event.type() == QtCore.QEvent.Close:
            self.close()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._clear_input_focus()
        super().mousePressEvent(event)

    def _input_focus_widget_types(self):
        return (
            QtWidgets.QLineEdit,
            QtWidgets.QAbstractSpinBox,
            QtWidgets.QComboBox,
        )

    def _is_inside_input_widget(self, widget):
        current = widget
        input_types = self._input_focus_widget_types()
        while current is not None and current is not self:
            if isinstance(current, input_types):
                return True
            current = current.parentWidget()
        return False

    def _clear_input_focus(self):
        focused_widget = QtWidgets.QApplication.focusWidget()
        if focused_widget is None or focused_widget is self:
            return
        if not self.isAncestorOf(focused_widget):
            return
        focused_widget.clearFocus()

    def _setup_focus_clear(self):
        parent = self.parent()
        if parent is not None:
            parent.installEventFilter(self)
        target = self.centralWidget()
        if target is not None:
            target.installEventFilter(self)
        for child in self.findChildren(QtWidgets.QWidget):
            if child is target:
                continue
            if self._is_inside_input_widget(child):
                continue
            child.installEventFilter(self)

    def create_guide(self):
        self.__set_name()
        guide_name = self.__gd.create_guide(
            comp_type=self.__get_comp_type(),
            name=self.name,
            side=self.__get_side(),
            idx=self.__get_idx(),
            parent_root=self.__get_parent_root(),
        )
        if guide_name:
            self.__gd.apply_pre_settings(
                self.__get_comp_type(),
                guide_name,
            )
        self.__sync_idx_from_created_guide(guide_name)
        return guide_name

    @decorator.undo
    def create_guide_pos(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        if not nodes:
            cmds.warning("Nothing selected.")
            return
        for i_node in nodes:
            guide_name = self.create_guide()
            if not guide_name:
                return
            pos = cmds.xform(i_node, q=True, t=True, ws=True)
            cmds.xform(guide_name, t=pos, ws=True)

    @decorator.undo
    def __duplicate_guide(self, symmetrize=False):
        self.__gd.duplicate_guide(cmds.ls(sl=True, fl=True), symmetrize)
        self.__refresh_component_index()

    @decorator.undo
    def __delete_guide(self):
        self.__gd.delete_guide(cmds.ls(sl=True, fl=True))
        self.__refresh_component_index()

    @decorator.undo
    def __delete_guide_keep_children(self):
        self.__gd.delete_guide_keep_children(cmds.ls(sl=True, fl=True))
        self.__refresh_component_index()

    def __open_settings(self):
        self.__gd.open_settings(cmds.ls(sl=True, fl=True))

    def __open_pre_settings(self):
        self.__gd.open_pre_settings(
            comp_type=self.__get_comp_type(),
            parent_root=self.__get_parent_root(),
        )
        self.__update_pre_settings_btn()

    def __reset_pre_settings(self):
        reset = self.__gd.reset_pre_settings(
            comp_type=self.__get_comp_type(),
        )
        if not reset:
            cmds.warning("No pre-settings to reset.")
            return
        self.__update_pre_settings_btn()

    @decorator.undo
    def __extract_controls(self):
        self.__gd.extract_controls()

    @decorator.undo
    def __vanilla_build_guide(self):
        self.__gd.vanilla_build_guide()

    def __full_build_guide(self):
        self.__gd.full_build_guide()

    @decorator.undo
    def __fit_to_pos(self):
        self.__gd.fit_to_pos()

    @decorator.undo
    def __align_mid_pos(self):
        self.__gd.align_mid_pos()

    @decorator.undo
    def __fit_nearest(self):
        self.__gd.fit_nearest()

    @decorator.undo
    def __align_rot(self):
        self.__gd.align_rot()

    @decorator.undo
    def __align_mid_rot(self):
        self.__gd.align_mid_rot()

    @decorator.undo
    def __align_rot_nearest(self):
        self.__gd.align_rot_nearest()

    @decorator.undo
    def __aim_x(self):
        self.__gd.aim_x()

    @decorator.undo
    def __aim_y(self):
        self.__gd.aim_y()

    @decorator.undo
    def __aim_z(self):
        self.__gd.aim_z()

    def __on_solo_move_toggled(self, checked):
        self.__gd.set_preserve_children(checked)
        self.__update_solo_move_button_style(checked)

    def __update_solo_move_button_style(self, enabled):
        if enabled:
            self.__solo_move_btn.setStyleSheet(_SOLO_MOVE_ON_STYLE)
        else:
            self.__solo_move_btn.setStyleSheet("")

    def __lock_solo_move_button_size(self):
        btn = self.__solo_move_btn
        if not btn or self.__solo_move_size_locked:
            return

        enabled = btn.isChecked()

        btn.setStyleSheet(_SOLO_MOVE_ON_STYLE)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        on_size = btn.sizeHint()

        btn.setStyleSheet("")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        off_size = btn.sizeHint()

        height = max(on_size.height(), off_size.height())
        btn.setFixedHeight(height)

        self.__update_solo_move_button_style(enabled)
        self.__solo_move_size_locked = True

    def __sync_solo_move_button(self):
        if not self.__solo_move_btn:
            return
        enabled = self.__gd.get_preserve_children()
        self.__solo_move_btn.blockSignals(True)
        self.__solo_move_btn.setChecked(enabled)
        self.__update_solo_move_button_style(enabled)
        self.__solo_move_btn.blockSignals(False)

    def __wire_rotate_button(self, btn, axis):
        btn.clicked.connect(
            lambda x: self.__rotate_axis(axis, 90.0)
        )
        btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos: self.__rotate_axis(axis, -90.0)
        )

    @decorator.undo
    def __rotate_axis(self, axis, degrees):
        self.__gd.rotate_axis(axis, degrees)


def show(*args):
    window = GuidrawerUI()
    window.show()
    window.raise_()
    window.activateWindow()
