# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Resize Dlg
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU method to automatically resize 
    *                a dialog box
    * First release: 2019-07-26
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


import os
import json
import codecs

from .global_vars import *
from .global_fnc import *


class ResizeDlg:

    def __init__(self, dlg, dlg_param):
        
        self.dlg = dlg
        self.dlg_param = dlg_param
        self.resize_params = {}
        if self.dlg_param == "dlg_show_ptplots":
            self.sw = dlg_show_ptplots_sw
            self.sh = dlg_show_ptplots_sh
        if self.dlg_param == "dlg_show_capabilities":
            self.sw = dlg_show_capabilities_sw
            self.sh = dlg_show_capabilities_sh
        if self.dlg_param == "dlg_transfo_pt_to_plots":
            self.sw = dlg_transfo_pt_to_plots_sw
            self.sh = dlg_transfo_pt_to_plots_sh
        if self.dlg_param == "dlg_cut_oldlimit":
            self.sw = dlg_cut_oldlimit_sw
            self.sh = dlg_cut_oldlimit_sh
        self.wtbv = self.sw
        self.htbv = self.sh
    
    # Choose the type of automatic resizing
    def dlg_ch_resize(self):
        if self.resize_params[self.dlg_param]:  
            self.dlg_dft_resize()
            nw_resize = False
        else:
            self.dlg_auto_resize()
            nw_resize = True  
        self.resize_params[self.dlg_param] = nw_resize            
        self.save_dlgresize(self.resize_params)
        return nw_resize
        
    # Resize the dlg to the default size
    def dlg_dft_resize(self):
        self.dlg.hide()
        self.dlg.resize(self.sw, self.sh)
        self.dlg.show()
    
    # Resize the dlg to the max size of tableview
    def dlg_auto_resize(self):
        self.dlg.hide()
        self.dlg.resize(self.wtbv, self.htbv)
        self.dlg.show()
    
    # Loads params to check if a dlg must be automatically resized
    # Used for 3 dlg
    def load_dlgresize(self):
        params={}
        try:
            json_path = os.path.join(os.path.dirname(__file__), r"dlg_resize.json")
        except IOError as error:
            raise error
        with codecs.open(json_path, encoding='utf-8', mode='r') as json_file:
            json_dlg_resize = json.load(json_file)
            params["dlg_show_capabilities"] = json_dlg_resize[r"dlg_show_capabilities"]
            params["dlg_show_ptplots"] = json_dlg_resize[r"dlg_show_ptplots"]
            params["dlg_transfo_pt_to_plots"] = json_dlg_resize[r"dlg_transfo_pt_to_plots"]
            params["dlg_cut_oldlimit"] = json_dlg_resize[r"dlg_cut_oldlimit"]
            self.resize_params = params
        return self.resize_params
            
    # Save params in the json file
    def save_dlgresize(self, params):
        # Update the json file   
        try:
            json_path = os.path.join(os.path.dirname(__file__), r"dlg_resize.json")
        except IOError as error:
            raise error
        with codecs.open(json_path, encoding='utf-8', mode='w') as json_file:
            json_file.write(json.dumps(params, indent=4, separators=(',', ': '), ensure_ascii=False))