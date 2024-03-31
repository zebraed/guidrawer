#! /usr/bin/ python
# -*- coding: utf-8 -*-
__author__  = "zebraed / ro"
__version__ = "1.0.0"
__license__ = "MIT"


def reload():
    import sys
    for k in sys.modules.keys():
        if k.find("guidrawer") > -1:
            del sys.modules[k]
    print("# Reload: guidrawer")
