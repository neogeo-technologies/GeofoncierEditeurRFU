# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Refdoss and comment entry
    * Description:   Define a class that provides to the plugin
    *                the possibility to enter a refdoss and a comment
    * First release: 2019-07-19
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QObject
from qgis.PyQt.QtWidgets import QDialog

import os

from . import tools
from .global_vars import *
from .global_fnc import *

gui_dlg_refdoss_cmt, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_refdoss_cmt.ui"))


class RefDossCmtEntry(QDialog, gui_dlg_refdoss_cmt):
  
    send_refdoss_cmt_vals = pyqtSignal(dict)
    
    def __init__(self, parent=None):

        super(RefDossCmtEntry, self).__init__(parent)
        self.setupUi(self)
        # Initialization of the closing method (False= quit by red cross)
        self.quit_valid = False
        self.dic_vals = {}
        self.valid_btn.accepted.connect(self.butt_ok)
        self.valid_btn.rejected.connect(self.butt_cancel)
        # Delete Widget on close event..
        self.setAttribute(Qt.WA_DeleteOnClose)

    def closeEvent(self, event):
        self.dic_vals["refdoss"] = ''
        self.dic_vals["cmt"] = ''
        self.dic_vals["ok"] = False
        # Hide the window
        self.hide()
        self.send_refdoss_cmt_vals.emit(self.dic_vals)

    def butt_ok(self):
        self.dic_vals["refdoss"] = self.ref_led.text()
        self.dic_vals["cmt"] = self.cmt_led.text()
        self.dic_vals["ok"] = True
        self.hide()
        self.send_refdoss_cmt_vals.emit(self.dic_vals)
        
    def butt_cancel(self):
        self.close()