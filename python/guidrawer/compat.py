#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
import importlib
import sys

if sys.version_info.major == 3:
    reload = importlib.reload
    basestring = str
    unicode = str
else:
    reload = reload
    from future_builtins import map, filter
