# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3plugin
    * Module:        Login
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the Login dialog
    * First release: 2015
    * Last release:  2019-08-19
    * Copyright:     (C) 2015 Géofoncier(R), (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

import os
import xml.etree.ElementTree as ElementTree

from .client import APIClient
from .config import Configuration
from .global_fnc import *


gui_dlg_login, _ = uic.loadUiType(
                    os.path.join(os.path.dirname(__file__), r"gui/dlg_login.ui"))


class GeoFoncierAPILogin(QDialog, gui_dlg_login):

    closed = pyqtSignal()
    opened = pyqtSignal()

    def __init__(self, parent=None):

        super(GeoFoncierAPILogin, self).__init__(parent)
        self.setupUi(self)

        self.config = Configuration()
        self.conn = None

        if self.config.user:
            self.userLineEdit.setText(self.config.user)
            self.rememberMeCheckBox.setChecked(True)

        self.signInPushButton.clicked.connect(self.sign_in)

    def closeEvent(self, event):

        self.closed.emit()

    def sign_in(self):

        self.user = self.userLineEdit.text()
        
        self.pw = self.passwordLineEdit.text()

        self.conn = APIClient(user=self.user, pw=self.pw)

        if self.rememberMeCheckBox.isChecked():
            self.config.set_login_info(self.user, self.pw)
        else:
            self.config.erase_login_info()

        resp = self.conn.get_my_capabilities()
        if resp.code != 200:
            # Catch the error specified by the API..

            tree = ElementTree.fromstring(resp.read())
            elt_err = tree.find(r"./log")
            if elt_err.text:
                msg = elt_err.text
            else:
                # Error returned by the server (all other cases)..
                msg = str(resp)

            # Then display the error in a message box..
            return QMessageBox.warning(self, r"Connexion impossible", msg)

        tree = ElementTree.fromstring(resp.read())

        # On connection success, get user's capability informations..

        elt_extract = tree.find(r"./cle_api_rfu/extraction_rfu")
        if elt_extract.text == r"oui":
            self.conn.extract = True

        elt_extract_lim = tree.find(r"./cle_api_rfu/extraction_rfu_limite")
        if elt_extract_lim.text is not None:
            self.conn.extract_lim = int(elt_extract_lim.text)

        elt_update = tree.find(r"./cle_api_rfu/mise_a_jour_rfu")
        if elt_update.text == r"oui":
            self.conn.update = True

        # Then..
        self.accept()

        self.opened.emit()
