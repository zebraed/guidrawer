from mgear.vendor.Qt import QtCore


class Core(QtCore.QObject):
    sideChanged = QtCore.Signal(str)
    idxChanged = QtCore.Signal(int)
    compTypeChanged = QtCore.Signal(str)
    axisDirChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._delegate = None

        self._side = None
        self._idx = 0
        self._comp_type = None

        self._verbose = False

        self.__initialize()

    def __initialize(self):
        self._side = ComboBoxModel(self)
        self._comp_type = ComboBoxModel(self)
        self._axis_dir = ComboBoxDictModel(self)

        self._side.currntChanged.connect(self.__on_side_changed)
        self._comp_type.currntChanged.connect(self.__on_comp_type_changed)
        self._axis_dir.currntChanged.connect(self.__on_axis_dir_changed)

    def side_model(self):
        return self._side

    def comp_model(self):
        return self._comp_type

    def idx_model(self):
        return self._idx

    def axis_dir_model(self):
        return self._axis_dir

    def __on_side_changed(self, side):
        if self._verbose:
            print(f"__on_side_changed: > {side}")
        self.sideChanged.emit(side)

    def __on_comp_type_changed(self, comp_type):
        if self._verbose:
            print(f"__on_comp_type_changed: > {comp_type}")
        self.compTypeChanged.emit(comp_type)

    def __on_axis_dir_changed(self, axis_dir):
        if self._verbose:
            print(f"__on_axis_dir_changed: > {axis_dir}")
        self.axisDirChanged.emit(axis_dir)

    def isChain(self, comp_type):
        return comp_type.startswith("chain")


class ComboBoxModel(QtCore.QObject):
    listChanged = QtCore.Signal()
    currntChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._items = []
        self._current = None

    def setItems(self, item_list):
        self._items = item_list
        self._current = None
        self.listChanged.emit()

    def items(self):
        return self._items

    def current(self):
        return self._current

    def setCurrent(self, value):
        self._current = value
        self.currntChanged.emit(value if value else "")


class ComboBoxDictModel(QtCore.QObject):
    listChanged = QtCore.Signal()
    currntChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._items = []
        self._data = {}
        self._current = None

    def setItems(self, item_dict):
        self._items = list(item_dict.keys())
        self._data = item_dict
        self._current = None
        self.listChanged.emit()

    def items(self):
        return self._items

    def idxFromItem(self, item):
        return self._data[item]

    def current(self):
        return self._current

    def setCurrent(self, value):
        self._current = value
        self.currntChanged.emit(value if value else "")
