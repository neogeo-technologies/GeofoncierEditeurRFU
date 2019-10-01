# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Editor RFU Geofoncier
    * Description:   Initialization
    * First release: 2015
    * Last release:  2019-08-19
    * Copyright:     (C) 2015 Géofoncier(R), (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""


def classFactory(iface):
    from .editor_rfu_geofoncier import EditorRFUGeofoncier
    return EditorRFUGeofoncier(iface)
