#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-


# Copyright (C) 2015 Géofoncier (R)


def classFactory(iface):
    from .editor_rfu_geofoncier import EditorRFUGeofoncier
    return EditorRFUGeofoncier(iface)
