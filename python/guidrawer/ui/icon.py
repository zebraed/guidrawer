import os
from dataclasses import dataclass
from typing import Optional, Tuple

from mgear.vendor.Qt import QtCore, QtGui

from .. import shifter_bridge as bridge


_ICON_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "icons")


@dataclass(frozen=True)
class Icon:
    """Icon source with optional mGear lookup and tint color."""

    path: str
    mgear: bool = False
    tint: Optional[Tuple[int, int, int]] = None

    def __call__(self):
        """Return the configured QIcon."""
        path = self.path
        if self.mgear:
            path = bridge.get_mgear_icon_path(path)
            if not path:
                return QtGui.QIcon()

        if self.tint is None:
            return QtGui.QIcon(path)
        return self._tinted_qicon(path)

    def _tinted_qicon(self, path):
        source = QtGui.QPixmap(path)
        if source.isNull():
            return QtGui.QIcon()

        tinted = QtGui.QPixmap(source.size())
        tinted.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(tinted)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)
        painter.fillRect(tinted.rect(), QtGui.QColor(*self.tint))
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode_DestinationIn
        )
        painter.drawPixmap(0, 0, source)
        painter.end()

        return QtGui.QIcon(tinted)


@dataclass(frozen=True)
class IconSettings:
    """Icons used by Guidrawer UI."""

    window: Icon
    parent_root: Icon
    pre_settings: Icon
    reset_pre_settings: Icon
    create_guide: Icon
    settings: Icon
    duplicate_guide: Icon
    mirror_guide: Icon
    delete_guide: Icon
    delete_keep_child: Icon
    update_component: Icon
    guide_symmetry: Icon
    component_type_lister: Icon
    chain_utils: Icon
    temporary_unparent: Icon
    reparent: Icon
    vanilla_build: Icon
    full_build: Icon
    unbuild: Icon
    fit_to_pos: Icon
    align_mid_pos: Icon
    fit_nearest: Icon
    align_rot: Icon
    align_mid_rot: Icon
    align_rot_nearest: Icon
    aim: Icon
    rotate: Icon
    align_curve: Icon
    solo_move: Icon
    select_shape: Icon
    scale_shape: Icon
    edit_shape: Icon
    replace_shape: Icon
    mirror_shape: Icon
    extract_control: Icon


def __get_icon_path(name):
    return os.path.join(_ICON_DIR, name)


ICONS = IconSettings(
    # main icon
    window=Icon(__get_icon_path("guidrawer_icon.svg")),

    # tools icons
    parent_root=Icon(":/dopeSheetSelect.png"),
    pre_settings=Icon(":/RS_settings_pop.png"),
    reset_pre_settings=Icon(":/deletePreset.png"),
    create_guide=Icon(":/createBin.png"),
    settings=Icon(":/advancedSettings.png"),
    duplicate_guide=Icon(":/teCompDup.png"),
    mirror_guide=Icon(":/polySymmetrizeUV.png"),
    delete_guide=Icon(":/deleteRenderPass.png"),
    delete_keep_child=Icon(":/deletePCM.png"),
    update_component=Icon(":/updateBookmark.png"),
    guide_symmetry=Icon("mgear_guide_symmetry.svg", mgear=True),
    component_type_lister=Icon(
        "mgear_component_type_lister.svg", mgear=True
    ),
    chain_utils=Icon("mgear_chain_utils.svg", mgear=True),
    temporary_unparent=Icon(":/parent.png"),
    reparent=Icon(":/parent.png", tint=(120, 200, 255)),
    vanilla_build=Icon(":/HIKcreateCustRig.png"),
    full_build=Icon(":/HIKcreateControlRig.png"),
    unbuild=Icon(":/removeSkinInfluence.png"),
    fit_to_pos=Icon(":/pivotPos.png"),
    align_mid_pos=Icon(":/UVAlignMiddleV.png"),
    fit_nearest=Icon(":/pivotResetPos.png"),
    align_rot=Icon(":/pivotAlign.png"),
    align_mid_rot=Icon(":/polyAlignUVLinear.png"),
    align_rot_nearest=Icon(":/pivotResetOri.png"),
    aim=Icon(":/poleVectorConstraint.png"),
    rotate=Icon(":/rotate_M.png"),
    align_curve=Icon(":/align.png"),
    solo_move=Icon(":/move_M.png"),
    select_shape=Icon(":/lassoSelect.png"),
    scale_shape=Icon(":/modifyScaleCurvature.png"),
    edit_shape=Icon(":/textureEditorShortestEdgePath.png"),
    replace_shape=Icon(":/isolateCurve.png"),
    mirror_shape=Icon(":/out_alignCurve.png"),
    extract_control=Icon(":/extend.png"),
)
