#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
from collections import OrderedDict


VALID_SIDE_INDEX_LIST = ["C", "L", "R"]
VALID_AXIS_INDEX_DICT = OrderedDict((("+X", 0), ("-X", 3), ("+Y", 1),
                                    ("-Y", 4), ("+Z", 2), ("-Z", 5)))
GUIDE_ROOT_NAME_CONV = "{name}_{side}{idx}_root"
