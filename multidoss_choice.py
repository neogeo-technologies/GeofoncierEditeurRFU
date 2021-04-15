# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Multidoss choice
    * Description:   Define a class that provides to the plugin
    *                the possibility to choice one ref_doss among several doss
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

gui_dlg_multidoss_choice, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_multidoss.ui"))


class MultiDossChoice(QDialog, gui_dlg_multidoss_choice):
  
    send_refapidoss = pyqtSignal(str)
    
    def __init__(self, doss_infos, parent=None):

        super(MultiDossChoice, self).__init__(parent)
        self.doss_infos = doss_infos
        self.setupUi(self)
        # Initialization of the closing method (False= quit by red cross)
        self.quit_valid = False
        self.refapidoss = ""
        self.validBtn.accepted.connect(self.butt_ok)
        self.validBtn.rejected.connect(self.butt_cancel)
        # Delete Widget on close event..
        self.setAttribute(Qt.WA_DeleteOnClose)       
        # Fill the combobox
        self.cabrefCmb.clear()
        for doss in self.doss_infos:
            doss_txt = "Cabinet: %s | Référence dossier: %s" % (doss[0], doss[1])
            self.cabrefCmb.addItem(doss_txt)
        self.cabrefCmb.setCurrentIndex(0)

    def closeEvent(self, event):
        # Hide the window
        self.hide()
        self.send_refapidoss.emit(self.refapidoss)

    def butt_ok(self):
        self.refapidoss = self.doss_infos[self.cabrefCmb.currentIndex()][2]
        self.hide()
        self.send_refapidoss.emit(self.refapidoss)
        
    def butt_cancel(self):
        self.close()