#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from PySide2 import QtWidgets, QtCore


class HorizontalLine(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        super(HorizontalLine, self).__init__(*args, **kwargs)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


class ComboBox(QtWidgets.QComboBox):
    def __init__(self, model, parent=None):
        super(ComboBox, self).__init__(parent=parent)
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
        self.button = QtWidgets.QPushButton(button_label_text,)
        super(TextFieldButton, self).__init__(parent=parent)
        #self.button.clicked.connect(self.__set_text)


class FloatSlider(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(float)

    def __init__(self, *args, **kwargs):
        super(FloatSlider, self).__init__(*args, **kwargs)
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
