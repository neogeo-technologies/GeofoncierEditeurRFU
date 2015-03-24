#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os

from PyQt4 import uic
from PyQt4.QtGui import QDialog


gui_dlg_edge_attrib_creator, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_edge_attrib_creator.ui"))


class EdgeAttribCreator(QDialog, gui_dlg_edge_attrib_creator):

    def __init__(self, parent=None, user=None, auth_creator=[]):

        super(EdgeAttribCreator, self).__init__(parent)
        self.setupUi(self)

        self.user = user
        self.auth_creator = auth_creator

        self.som_ge_createur = None

        # Attribute: `som_createur`
        for i, e in enumerate(self.auth_creator):
            self.creatorComboBox.addItem(u"%s (%s)" % (e[1], e[0]))
            if user == e[0]:
                self.creatorComboBox.setCurrentIndex(i)

        self.buttonBox.accepted.connect(self.on_accepted)
        self.buttonBox.rejected.connect(self.on_rejected)

    def on_accepted(self):

        self.som_ge_createur = self.auth_creator[self.creatorComboBox.currentIndex()][0]
        self.accept()

    def on_rejected(self):
        self.reject()
