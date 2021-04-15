# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Editor RFU Geofoncier
    * Description:   Initialization
    * First release: 2015
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


def classFactory(iface):
    from .editor_rfu_geofoncier import EditorRFUGeofoncier
    return EditorRFUGeofoncier(iface)
