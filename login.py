#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os
import xml.etree.ElementTree as ElementTree

from PyQt4 import uic
from PyQt4.QtGui import QDialog

from client import APIClient
from config import Configuration


gui_dlg_login, _ = uic.loadUiType(
                    os.path.join(os.path.dirname(__file__), r"gui/dlg_login.ui"))


class GeoFoncierAPILogin(QDialog, gui_dlg_login):

    def __init__(self, parent=None):

        super(GeoFoncierAPILogin, self).__init__(parent)
        self.setupUi(self)

        self.config = Configuration()
        self.conn = None

        if self.config.user and self.config.pw:
            self.userLineEdit.setText(self.config.user)
            self.passwordLineEdit.setText(self.config.pw)
            self.rememberMeCheckBox.setChecked(True)

        self.signInPushButton.clicked.connect(self.sign_in)

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

            elt_err = tree.find(r"./erreur")
            if elt_err.text:
                msg = elt_err.text
            else:
                # Error returned by the server (all other cases)..
                msg = str(resp)

            # Then display the error in a message box..
            return QtGui.QMessageBox.warning(self, r"Warning", msg)

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
