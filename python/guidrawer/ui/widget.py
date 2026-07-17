from mgear.vendor.Qt import QtCore, QtGui, QtWidgets


_GROUP_BG_DARK = QtGui.QColor(68, 68, 68)
_GROUP_BG_LIGHT = QtGui.QColor(73, 73, 73)
_GROUP_BORDER = QtGui.QColor(87, 87, 87)


class HorizontalLine(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


class ToolPushButton(QtWidgets.QPushButton):
    """Push button with distinct left-click and right-click actions."""

    rightClicked = QtCore.Signal()

    def __init__(
        self,
        text,
        left_click_text,
        right_click_text,
        parent=None,
    ):
        super().__init__(text, parent=parent)
        self.setToolTip(
            f"Left Click: {left_click_text}\n"
            f"Right Click: {right_click_text}"
        )
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._emit_right_clicked)

    def _emit_right_clicked(self, _pos):
        self.rightClicked.emit()


class CollapsibleGroupBox(QtWidgets.QGroupBox):
    """Collapsible group box with transfer_controller-style header."""

    toggled = QtCore.Signal(bool)
    _HEADER_HEIGHT = 20

    def __init__(self, title="", parent=None):
        super().__init__(title, parent=parent)
        self._expanded = True
        self._content_frame = None
        self._header_hovered = False
        self.setMouseTracking(True)

    def set_content_frame(self, frame):
        self._content_frame = frame

    def is_expanded(self):
        return self._expanded

    def set_expanded(self, expanded):
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._apply_expanded_state()
        if self._expanded:
            self._header_hovered = False
        else:
            self._update_header_hover(self.mapFromGlobal(QtGui.QCursor.pos()))
        self.toggled.emit(self._expanded)
        self.update()

    def _apply_expanded_state(self):
        if self._content_frame is not None:
            self._content_frame.setVisible(self._expanded)
        if self._expanded:
            self.setMaximumHeight(16777215)
        else:
            self.setMaximumHeight(self._HEADER_HEIGHT)

    def _header_rect(self):
        return QtCore.QRect(0, 0, self.width(), self._HEADER_HEIGHT)

    def _is_highlighted(self):
        return self._expanded or self._header_hovered

    def _update_header_hover(self, pos):
        hovered = self._header_rect().contains(pos)
        if hovered == self._header_hovered:
            return
        self._header_hovered = hovered
        self.update()

    def enterEvent(self, event):
        if not self._expanded:
            self._update_header_hover(self.mapFromGlobal(QtGui.QCursor.pos()))
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._header_hovered:
            self._header_hovered = False
            self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        if not self._expanded:
            self._update_header_hover(event.pos())
        elif self._header_hovered:
            self._header_hovered = False
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        header_rect = QtCore.QRectF(0, 0, self.width(), self._HEADER_HEIGHT)
        if header_rect.contains(event.pos()):
            self.set_expanded(not self._expanded)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        border_color = QtGui.QColor(_GROUP_BORDER)
        if self._is_highlighted():
            border_color.setRed(border_color.red() + 30)
            border_color.setGreen(border_color.green() + 30)
            border_color.setBlue(border_color.blue() + 30)

        bg_rect = QtCore.QRectF(0, 0, self.width(), self.height())
        bg_rect.adjust(1, 1, -1, -1)
        painter.fillRect(bg_rect, _GROUP_BG_DARK)
        bg_rect.adjust(4, 22, -4, -4)
        painter.fillRect(bg_rect, _GROUP_BG_LIGHT)

        border_rect = QtCore.QRectF(0, 0, self.width(), self.height())
        border_rect.adjust(1, 1, -1, -1)
        painter.setPen(QtGui.QPen(border_color, 2))
        painter.drawRoundedRect(border_rect, 1, 1)

        header_rect = QtCore.QRectF(0, 0, self.width(), self._HEADER_HEIGHT)
        header_rect.adjust(1, 1, -1, 0)
        painter.fillRect(header_rect, border_color)

        font = QtGui.QFont(self.font())
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)

        if self._is_highlighted() and self.isEnabled():
            painter.setPen(QtGui.QColor(200, 200, 200))
        else:
            painter.setPen(QtGui.QColor(130, 130, 130))

        text_rect = QtCore.QRect(22, 1, self.width() - 24, self._HEADER_HEIGHT - 1)
        painter.drawText(text_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.title())

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(238, 238, 238))
        if self._expanded:
            triangle = [
                QtCore.QPoint(8, 7),
                QtCore.QPoint(16, 7),
                QtCore.QPoint(12, 13),
            ]
        else:
            triangle = [
                QtCore.QPoint(8, 5),
                QtCore.QPoint(8, 13),
                QtCore.QPoint(14, 9),
            ]
        painter.drawPolygon(triangle)


def group_box_frame(title, parent=None, object_name=None):
    """Collapsible QGroupBox with inner QFrame."""
    group = CollapsibleGroupBox(title, parent=parent)
    if object_name:
        group.setObjectName(object_name)
    layout = QtWidgets.QVBoxLayout(group)
    layout.setSpacing(3)
    layout.setContentsMargins(3, 8, 3, 3)
    frame = QtWidgets.QFrame(group)
    frame.setFrameShape(QtWidgets.QFrame.NoFrame)
    frame.setFrameShadow(QtWidgets.QFrame.Raised)
    layout.addWidget(frame)
    group.set_content_frame(frame)
    return group, frame


class ComboBox(QtWidgets.QComboBox):
    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.__model = model
        self.__model.listChanged.connect(self.__modelChanged)
        self.currentIndexChanged.connect(self.__onCurrentIndexChanged)

    def setItems(self, items):
        self.__model.setItems(items)

    def reset(self):
        self.__modelChanged(cur=self.__model.current())

    def __onCurrentIndexChanged(self, idx):
        self.__onCurrentTextChanged(self.itemText(idx))

    def __onCurrentTextChanged(self, txt):
        self.__model.setCurrent(txt)

    def __modelChanged(self, cur=None):
        if cur is None:
            cur = self.currentText()

        self.blockSignals(True)
        self.clear()
        items = self.__model.items()
        self.addItems(items)
        if cur in items:
            self.setCurrentIndex(items.index(cur))

        self.blockSignals(False)

        if len(items) == 0:
            self.__model.setCurrent(None)
        else:
            self.__model.setCurrent(self.currentText())


class TextFieldButton(QtWidgets.QLineEdit):
    def __init__(self, button_label_text=None, parent=None):
        if button_label_text is None:
            button_label_text = "set"
        self.button = QtWidgets.QPushButton(button_label_text)
        super().__init__(parent=parent)


class FloatSlider(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.__spin_box = QtWidgets.QDoubleSpinBox(self)
        self.__spin_box.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        main_layout.addWidget(self.__spin_box)

        self.__slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.__update_slider()
        main_layout.addWidget(self.__slider)

        self.setDecimals(4)

        self.__spin_box.valueChanged[float].connect(self.valueChangedCallback)
        self.__slider.valueChanged[int].connect(self.valueChangedCallback)

    def valueChangedCallback(self, value):
        _sender = self.sender()
        if _sender == self.__spin_box:
            self.__slider.blockSignals(True)
            self.__slider.setValue(value * self.__boost)
            self.__slider.blockSignals(False)
        elif _sender == self.__slider:
            value = float(value) / self.__boost
            self.__spin_box.blockSignals(True)
            self.__spin_box.setValue(value)
            self.__spin_box.blockSignals(False)
        self.valueChanged.emit(value)

    def value(self):
        return self.__spin_box.value()

    def setValue(self, value):
        self.__spin_box.setValue(value)

    def setRange(self, _min, _max):
        self.__spin_box.setRange(_min, _max)
        self.__update_slider()

    def setDecimals(self, prec):
        self.__spin_box.setDecimals(prec)
        self.__update_slider()

    def __update_slider(self):
        dec = self.__spin_box.decimals()
        _min = self.__spin_box.minimum()
        _max = self.__spin_box.maximum()
        self.__boost = int("1" + ("0" * dec))
        self.__slider.setRange(_min * self.__boost, _max * self.__boost)
