"""Multiple Drawing the mGear's Guide Component."""
import json
import os

from maya import cmds

from mgear.vendor.Qt import QtCore, QtGui, QtWidgets

from .. import const
from .. import decorator
from .. import drawer
from .. import maya_util
from . import model
from .. import shifter_bridge as bridge
from . import widget


ICON_PATH = os.path.join(
    os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
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
        self.__auto_side_group = None
        self.__auto_side_options_widget = None
        self.__auto_side_parent_rb = None
        self.__auto_side_pos_rb = None
        self.__pre_settings_btn = None
        self.__reset_pre_settings_btn = None
        self.__create_gd_btn = None
        self.__settings_btn = None
        self.__mir_gd_btn = None
        self.__dup_gd_btn = None
        self.__del_gd_btn = None
        self.__del_keep_child_gd_btn = None
        self.__update_component_btn = None
        self.__guide_symmetry_btn = None
        self.__component_type_lister_btn = None
        self.__chain_utils_btn = None
        self.__vanilla_build_btn = None
        self.__full_build_btn = None
        self.__unbuild_btn = None
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
        self.__align_crv_btn = None
        self.__solo_move_btn = None
        self.__sel_shape_btn = None
        self.__scale_shape_btn = None
        self.__edit_shape_btn = None
        self.__replace_shape_btn = None
        self.__mirror_shape_btn = None
        self.__extr_ctrl_btn = None

        self.__solo_move_size_locked = False

        self.__idx_updating = False
        self.__suppress_next_activate_refresh = False

        self._set_window_icon()

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

    def __settings_key(self):
        return f"{self.object_name}_settings"

    def __window_geometry_for_settings(self):
        frame = self.frameGeometry()
        geometry = self.geometry()
        return {
            "x": frame.x(),
            "y": frame.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }

    def __gather_settings(self):
        auto_side_mode = self.__get_auto_side_mode()
        if self.__auto_side_group and not self.__auto_side_group.isChecked():
            auto_side_mode = None

        return {
            "window_geometry": self.__window_geometry_for_settings(),
            "component_type": self.__get_comp_type(),
            "base_name": self.__get_base_name(),
            "side": self.__get_side(),
            "index": self.__get_idx(),
            "parent_root": self.__get_parent_root(),
            "auto_side_enabled": bool(
                self.__auto_side_group
                and self.__auto_side_group.isChecked()
            ),
            "auto_side_mode": auto_side_mode,
        }

    def __set_combo_text(self, combo, text):
        if not combo or not text:
            return
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)

    def __apply_settings(self, settings):
        if not isinstance(settings, dict):
            return

        geometry = settings.get("window_geometry")
        if isinstance(geometry, dict):
            self.resize(
                int(geometry.get("width", self.width())),
                int(geometry.get("height", self.height())),
            )
            self.move(
                int(geometry.get("x", self.x())),
                int(geometry.get("y", self.y())),
            )

        self.__set_combo_text(
            self.__comp_cmb_widget,
            settings.get("component_type"),
        )
        self.__base_name_le_wiget.setText(settings.get("base_name", ""))
        self.__set_combo_text(self.__side_cmb_widget, settings.get("side"))
        self.__parent_root_le_widget.setText(settings.get("parent_root", ""))

        auto_side_enabled = bool(settings.get("auto_side_enabled", False))
        auto_side_mode = settings.get("auto_side_mode")
        self.__auto_side_group.blockSignals(True)
        self.__auto_side_parent_rb.blockSignals(True)
        self.__auto_side_pos_rb.blockSignals(True)
        self.__auto_side_group.setChecked(auto_side_enabled)
        self.__auto_side_options_widget.setVisible(auto_side_enabled)
        if auto_side_mode == "pos":
            self.__auto_side_pos_rb.setChecked(True)
        elif auto_side_mode == "parent":
            self.__auto_side_parent_rb.setChecked(True)
        else:
            self.__auto_side_parent_rb.setChecked(False)
            self.__auto_side_pos_rb.setChecked(False)
        self.__auto_side_pos_rb.blockSignals(False)
        self.__auto_side_parent_rb.blockSignals(False)
        self.__auto_side_group.blockSignals(False)

        index = settings.get("index")
        if isinstance(index, int):
            self.__set_idx(index)

    def __save_settings(self):
        data = self.__gather_settings()
        cmds.optionVar(sv=(self.__settings_key(), json.dumps(data)))

    def __load_settings(self):
        key = self.__settings_key()
        if not cmds.optionVar(exists=key):
            return
        raw = cmds.optionVar(q=key)
        if isinstance(raw, (list, tuple)) and raw:
            raw = raw[0]
        if not isinstance(raw, str) or not raw:
            return
        self.__apply_settings(json.loads(raw))

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

        self.__auto_side_group = QtWidgets.QGroupBox("Auto Side Label", parent=opt_widget)
        self.__auto_side_group.setCheckable(True)
        self.__auto_side_group.setChecked(False)

        auto_side_group_layout = QtWidgets.QVBoxLayout(self.__auto_side_group)
        auto_side_group_layout.setContentsMargins(8, 4, 8, 4)
        auto_side_group_layout.setSpacing(4)

        self.__auto_side_options_widget = QtWidgets.QWidget(
            parent=self.__auto_side_group
        )
        auto_side_layout = QtWidgets.QHBoxLayout(self.__auto_side_options_widget)
        auto_side_layout.setContentsMargins(0, 0, 0, 0)
        self.__auto_side_parent_rb = QtWidgets.QRadioButton("from parent")
        self.__auto_side_pos_rb = QtWidgets.QRadioButton("from pos")
        auto_side_button_group = QtWidgets.QButtonGroup(self.__auto_side_group)
        auto_side_button_group.addButton(self.__auto_side_parent_rb)
        auto_side_button_group.addButton(self.__auto_side_pos_rb)
        auto_side_layout.addWidget(self.__auto_side_parent_rb)
        auto_side_layout.addWidget(self.__auto_side_pos_rb)
        auto_side_layout.addStretch(1)
        auto_side_group_layout.addWidget(self.__auto_side_options_widget)
        self.__auto_side_options_widget.setVisible(False)

        self.__auto_side_group.toggled.connect(self.__on_auto_side_enabled)
        self.__auto_side_parent_rb.toggled.connect(
            self.__refresh_component_index
        )
        self.__auto_side_pos_rb.toggled.connect(
            self.__refresh_component_index
        )

        main_option_layout.addWidget(self.__auto_side_group)

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

        for col in range(2):
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

        self.__update_component_btn = QtWidgets.QPushButton("Update Component")
        self.__update_component_btn.setIcon(
            QtGui.QIcon(":/updateBookmark.png")
        )
        self.__update_component_btn.clicked.connect(
            lambda x: self.__update_component_type()
        )

        self.__guide_symmetry_btn = QtWidgets.QPushButton("Guide Symmetry")
        self.__guide_symmetry_btn.setIcon(
            self.__mgear_icon("mgear_guide_symmetry.svg")
        )
        self.__guide_symmetry_btn.clicked.connect(
            lambda x: self.__open_guide_symmetry_tool()
        )

        update_tools_layout = QtWidgets.QHBoxLayout()
        update_tools_layout.setContentsMargins(0, 0, 0, 0)
        update_tools_layout.addWidget(self.__update_component_btn)
        update_tools_layout.addWidget(self.__guide_symmetry_btn)

        self.__component_type_lister_btn = QtWidgets.QPushButton(
            "Comp Type Lister"
        )
        self.__component_type_lister_btn.setIcon(
            self.__mgear_icon("mgear_component_type_lister.svg")
        )
        self.__component_type_lister_btn.clicked.connect(
            lambda x: self.__open_component_type_lister()
        )

        self.__chain_utils_btn = QtWidgets.QPushButton("Chain Utils")
        self.__chain_utils_btn.setIcon(
            self.__mgear_icon("mgear_chain_utils.svg")
        )
        self.__chain_utils_btn.clicked.connect(
            lambda x: self.__open_chain_utils()
        )

        guide_tools_layout = QtWidgets.QHBoxLayout()
        guide_tools_layout.setContentsMargins(0, 0, 0, 0)
        guide_tools_layout.addWidget(self.__component_type_lister_btn)
        guide_tools_layout.addWidget(self.__chain_utils_btn)

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
        self.__wire_full_build_button(self.__full_build_btn)

        build_layout = QtWidgets.QHBoxLayout()
        build_layout.setContentsMargins(0, 0, 0, 0)
        build_layout.addWidget(self.__vanilla_build_btn)
        build_layout.addWidget(self.__full_build_btn)

        self.__unbuild_btn = QtWidgets.QPushButton("Unbuild")
        self.__unbuild_btn.setIcon(QtGui.QIcon(":/removeSkinInfluence.png"))
        self.__unbuild_btn.clicked.connect(
            lambda x: self.__unbuild_guide()
        )

        tools_inner_layout.addLayout(button_layout)
        tools_inner_layout.addLayout(delete_layout)
        tools_inner_layout.addLayout(update_tools_layout)
        tools_inner_layout.addLayout(guide_tools_layout)
        tools_inner_layout.addWidget(self.__hl_frame3)
        tools_inner_layout.addLayout(build_layout)
        tools_inner_layout.addWidget(self.__unbuild_btn)

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

        self.__align_crv_btn = QtWidgets.QPushButton("Align Crv")
        self.__align_crv_btn.setIcon(QtGui.QIcon(":/align.png"))
        self.__align_crv_btn.clicked.connect(
            lambda x: self.__align_curve()
        )
        align_layout.addWidget(self.__align_crv_btn, 4, 0, 1, 3)

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

        shape_group, shape_frame = widget.group_box_frame(
            "Controller Shape Tools",
            self.__main_widget,
            "controllerShapeTools",
        )
        shape_group.toggled.connect(self.__on_collapsible_group_toggled)
        shape_inner_layout = QtWidgets.QVBoxLayout(shape_frame)
        shape_inner_layout.setSpacing(0)
        shape_inner_layout.setContentsMargins(0, 0, 0, 0)

        shape_layout = QtWidgets.QGridLayout()
        shape_layout.setSizeConstraint(
            QtWidgets.QLayout.SetFixedSize
        )

        self.__sel_shape_btn = QtWidgets.QPushButton("Sel Shape")
        self.__sel_shape_btn.setIcon(QtGui.QIcon(":/lassoSelect.png"))
        self.__sel_shape_btn.clicked.connect(
            lambda x: self.__select_controller_shapes()
        )
        shape_layout.addWidget(self.__sel_shape_btn, 0, 0)

        self.__scale_shape_btn = QtWidgets.QPushButton("Scale Shape")
        self.__scale_shape_btn.setIcon(
            QtGui.QIcon(":/modifyScaleCurvature.png")
        )
        self.__wire_scale_shape_button(self.__scale_shape_btn)
        shape_layout.addWidget(self.__scale_shape_btn, 0, 1)

        self.__edit_shape_btn = QtWidgets.QPushButton("Edit")
        self.__edit_shape_btn.setIcon(
            QtGui.QIcon(":/textureEditorShortestEdgePath.png")
        )
        self.__edit_shape_btn.clicked.connect(
            lambda x: self.__toggle_controller_edit_mode()
        )
        shape_layout.addWidget(self.__edit_shape_btn, 0, 2)

        self.__replace_shape_btn = QtWidgets.QPushButton("Replace")
        self.__replace_shape_btn.setIcon(QtGui.QIcon(":/isolateCurve.png"))
        self.__replace_shape_btn.clicked.connect(
            lambda x: self.__replace_control_shape()
        )
        shape_layout.addWidget(self.__replace_shape_btn, 1, 0)

        self.__mirror_shape_btn = QtWidgets.QPushButton("Mirror Shape")
        self.__mirror_shape_btn.setIcon(QtGui.QIcon(":/out_alignCurve.png"))
        self.__mirror_shape_btn.clicked.connect(
            lambda x: self.__mirror_control_shape()
        )
        shape_layout.addWidget(self.__mirror_shape_btn, 1, 1)

        self.__extr_ctrl_btn = QtWidgets.QPushButton("Extr. Ctrl")
        self.__extr_ctrl_btn.setIcon(QtGui.QIcon(":/extend.png"))
        self.__extr_ctrl_btn.clicked.connect(
            lambda x: self.__extract_controls()
        )
        shape_layout.addWidget(self.__extr_ctrl_btn, 1, 2)

        for col in range(3):
            shape_layout.setColumnStretch(col, 1)

        shape_inner_layout.addLayout(shape_layout)

        central_layout = QtWidgets.QVBoxLayout(self.__main_widget)
        central_layout.setAlignment(QtCore.Qt.AlignTop)
        central_layout.setContentsMargins(10, 10, 10, 10)
        central_layout.setSpacing(5)
        central_layout.addWidget(opt_widget, 0)
        central_layout.addWidget(tools_group, 0)
        central_layout.addSpacing(8)
        central_layout.addWidget(align_group, 0)
        central_layout.addSpacing(8)
        central_layout.addWidget(shape_group, 0)

        self.__core.sideChanged.connect(self.__on_side_changed)
        self.__core.compTypeChanged.connect(self.__on_comp_type_changed)

        self.current_comp_type = self.__get_comp_type()
        self.__refresh_component_index()
        self.__sync_solo_move_button()
        self.__update_pre_settings_btn()
        self.__update_full_build_btn()
        self.__update_unbuild_btn()

    def __update_full_build_btn(self):
        if not self.__full_build_btn:
            return
        self.__full_build_btn.setEnabled(self.__gd.has_full_build_steps())

    def __update_unbuild_btn(self):
        if not self.__unbuild_btn:
            return
        self.__unbuild_btn.setEnabled(self.__gd.has_built_rig())

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
            side=self.__resolve_draw_side(),
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
            side=self.__resolve_draw_side(),
            parent_root=self.__get_parent_root(),
            start_index=value,
        )
        if valid_idx != value:
            self.__set_idx(valid_idx)

    def __sync_idx_from_created_guide(self, guide_root, side=None):
        if side is None and guide_root and cmds.objExists(f"{guide_root}.comp_side"):
            side = cmds.getAttr(f"{guide_root}.comp_side")
        if side is None:
            side = self.__resolve_draw_side()
        next_idx = self.__gd.get_next_component_index(
            comp_type=self.__get_comp_type(),
            name=self.__get_base_name(),
            side=side,
            parent_root=self.__get_parent_root(),
        )
        self.__set_idx(next_idx)

    def __get_base_name(self):
        return self.__base_name_le_wiget.text()

    def __get_side(self):
        return self.__side_cmb_widget.currentText()

    def __get_auto_side_mode(self):
        if not self.__auto_side_group or not self.__auto_side_group.isChecked():
            return None
        if self.__auto_side_parent_rb and self.__auto_side_parent_rb.isChecked():
            return "parent"
        if self.__auto_side_pos_rb and self.__auto_side_pos_rb.isChecked():
            return "pos"
        return None

    def __on_auto_side_enabled(self, enabled):
        if self.__auto_side_options_widget:
            self.__auto_side_options_widget.setVisible(enabled)
        if enabled:
            if (
                self.__auto_side_parent_rb
                and self.__auto_side_pos_rb
                and not self.__auto_side_parent_rb.isChecked()
                and not self.__auto_side_pos_rb.isChecked()
            ):
                self.__auto_side_parent_rb.setChecked(True)
        self.__refresh_component_index()
        QtCore.QTimer.singleShot(0, self.__lock_window_height)

    def __get_draw_parent_node(self, parent_root=None):
        if parent_root is None:
            parent_root = self.__get_parent_root().strip()
        else:
            parent_root = str(parent_root).strip()

        if parent_root:
            validated = bridge.validate_guide(parent_root)
            if validated:
                return validated
        return bridge.resolve_draw_parent("")

    def __resolve_draw_side(self, parent_root=None, position_node=None):
        mode = self.__get_auto_side_mode()
        if mode is None:
            return self.__get_side()

        if mode == "parent":
            parent = self.__get_draw_parent_node(parent_root)
            world_x = bridge.get_node_world_x(parent)
            return bridge.side_from_world_x(world_x)

        if position_node:
            world_x = bridge.get_node_world_x(position_node)
            return bridge.side_from_world_x(world_x)

        selection = cmds.ls(sl=True, fl=True)
        if selection:
            world_x = bridge.get_node_world_x(selection[-1])
            return bridge.side_from_world_x(world_x)

        parent = self.__get_draw_parent_node(parent_root)
        world_x = bridge.get_node_world_x(parent)
        return bridge.side_from_world_x(world_x)

    def __get_draw_index(self, side, parent_root=None):
        if parent_root is None:
            parent_root = self.__get_parent_root()
        return self.__gd.get_next_component_index(
            comp_type=self.__get_comp_type(),
            name=self.__get_base_name(),
            side=side,
            parent_root=parent_root,
        )

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
        self.__suppress_next_activate_refresh = True
        self.__sync_solo_move_button()
        self.__update_full_build_btn()
        self.__update_unbuild_btn()
        self.shrink()
        super().show()
        QtCore.QTimer.singleShot(0, self.__finalize_window_layout)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowActivate:
            if self.__suppress_next_activate_refresh:
                self.__suppress_next_activate_refresh = False
            else:
                self.__refresh_component_index()
            self.__sync_solo_move_button()
            self.__update_pre_settings_btn()
            self.__update_full_build_btn()
            self.__update_unbuild_btn()

    def restore(self):
        try:
            self.__load_settings()
        except Exception as exc:
            cmds.warning(f"Failed to load Guidrawer settings: {exc}")

    def closeEvent(self, event):
        try:
            self.__save_settings()
        except Exception as exc:
            cmds.warning(f"Failed to save Guidrawer settings: {exc}")
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

    def create_guide(self, parent_root=None, position_node=None):
        self.__set_name()
        if parent_root is None:
            parent_root = self.__get_parent_root()
        side = self.__resolve_draw_side(
            parent_root=parent_root,
            position_node=position_node,
        )
        idx = self.__get_draw_index(side, parent_root=parent_root)
        guide_name = self.__gd.create_guide(
            comp_type=self.__get_comp_type(),
            name=self.name,
            side=side,
            idx=idx,
            parent_root=parent_root,
        )
        if guide_name:
            self.__gd.apply_pre_settings(
                self.__get_comp_type(),
                guide_name,
            )
        self.__sync_idx_from_created_guide(guide_name, side=side)
        return guide_name

    @decorator.undo
    def create_guide_pos(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]

        if not nodes:
            guide_name = self.create_guide()
            if not guide_name:
                return
            parent_text = self.__get_parent_root().strip()
            if parent_text:
                validated = bridge.validate_guide(parent_text)
                if validated:
                    bridge.set_guide_to_parent_origin(guide_name)
            return

        parent_text = self.__get_parent_root().strip()
        for i_node in nodes:
            draw_parent = parent_text
            if not draw_parent:
                draw_parent = bridge.get_draw_parent_from_selection(i_node)
                if draw_parent is None:
                    draw_parent = ""
            guide_name = self.create_guide(
                parent_root=draw_parent,
                position_node=i_node,
            )
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

    def __select_controller_shapes(self):
        self.__gd.select_controller_shapes()

    @decorator.undo
    def __scale_controller_shapes(self, delta):
        self.__gd.scale_controller_shapes(delta)

    def __toggle_controller_edit_mode(self):
        self.__gd.toggle_controller_edit_mode()

    def __replace_control_shape(self):
        self.__gd.replace_control_shape()

    def __mirror_control_shape(self):
        self.__gd.mirror_control_shape()

    def __update_component_type(self):
        self.__gd.update_component_type()

    def __open_guide_symmetry_tool(self):
        self.__gd.open_guide_symmetry_tool()

    def __open_component_type_lister(self):
        self.__gd.open_component_type_lister()

    def __open_chain_utils(self):
        self.__gd.open_chain_utils()

    @staticmethod
    def __mgear_icon(icon_name):
        icon_path = bridge.get_mgear_icon_path(icon_name)
        if icon_path:
            icon = QtGui.QIcon(icon_path)
            if not icon.isNull():
                return icon
        return QtGui.QIcon()

    @decorator.undo
    def __vanilla_build_guide(self):
        self.__gd.vanilla_build_guide()
        self.__update_unbuild_btn()

    def __full_build_guide(self, with_log=False):
        self.__gd.full_build_guide(with_log=with_log)
        self.__update_unbuild_btn()

    @decorator.undo
    def __unbuild_guide(self):
        self.__gd.unbuild_guide()
        self.__update_unbuild_btn()

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

    def __wire_scale_shape_button(self, btn):
        btn.clicked.connect(
            lambda x: self.__scale_controller_shapes(0.1)
        )
        btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos: self.__scale_controller_shapes(-0.1)
        )

    def __wire_full_build_button(self, btn):
        btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos: self.__full_build_guide(with_log=True)
        )

    @decorator.undo
    def __rotate_axis(self, axis, degrees):
        self.__gd.rotate_axis(axis, degrees)

    @decorator.undo
    def __align_curve(self):
        self.__gd.align_curve()


def show(*args):
    window = GuidrawerUI()
    window.show()
    window.raise_()
    window.activateWindow()
