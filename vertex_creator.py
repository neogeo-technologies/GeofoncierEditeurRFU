#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os

from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import QPyNullVariant
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QTextCharFormat

from qgis.core import QgsFeature
from qgis.core import QgsGeometry
from qgis.core import QgsPoint

import tools


gui_dlg_vertex_creator, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_vertex_creator.ui"))


class VertexCreator(QDialog, gui_dlg_vertex_creator):

    def __init__(self, canvas, l_vertex, parent=None, user=None,
                 precision_class=[], ellips_acronym=[],
                 selected_ellips_acronym = None,
                 nature=[], auth_creator=[]):

        super(VertexCreator, self).__init__(parent)
        self.setupUi(self)

        self.canvas = canvas
        self.l_vertex = l_vertex
        self.user = user
        self.precision_class = precision_class
        self.ellips_acronym = ellips_acronym
        self.selected_ellips_acronym = selected_ellips_acronym
        self.nature = nature
        self.auth_creator = auth_creator

        self.xLineEdit.clear()
        self.yLineEdit.clear()

        print ellips_acronym

        for i, e in enumerate(self.ellips_acronym):
            self.ellipsComboBox.addItem(e[2])
            if not selected_ellips_acronym:
                continue
            if selected_ellips_acronym == e[0]:
                self.ellipsComboBox.setCurrentIndex(i)

        # Attribute: `som_precision_rattachement`
        for e in self.precision_class:
            self.precisionClassComboBox.addItem(e[1])

        # Attribute: `som_nature`
        for e in self.nature:
            self.natureComboBox.addItem(e)

        # Attribute: `som_createur`
        for i, e in enumerate(self.auth_creator):
            self.creatorComboBox.addItem(u"%s (%s)" % (e[1], e[0]))
            # Set current user as the creator by default..
            if user == e[0]:
                self.creatorComboBox.setCurrentIndex(i)

        self.buttonBox.accepted.connect(self.on_accepted)
        self.buttonBox.rejected.connect(self.on_rejected)

    def on_accepted(self):

        # Check if coordinates are entered..
        if not self.xLineEdit.text() or not self.yLineEdit.text():

            # (◕ε ◕ )

            pixmap = os.path.join(os.path.dirname(__file__), r"resources/underline.png")
            css = "QLabel {background: url(%s) bottom repeat-x;}" % pixmap

            self.xLabel.setTextFormat(Qt.RichText)
            self.xLabel.setStyleSheet(css)
            self.yLabel.setTextFormat(Qt.RichText)
            self.yLabel.setStyleSheet(css)

            return None

        # Set attributes..
        som_ge_createur = self.auth_creator[self.creatorComboBox.currentIndex()][0]
        som_nature = self.natureComboBox.currentText()
        som_coord_est = float(self.xLineEdit.text())
        som_coord_nord = float(self.yLineEdit.text())
        som_repres_plane = self.ellips_acronym[self.ellipsComboBox.currentIndex()][0]
        som_prec_rattcht = int(self.precision_class[self.precisionClassComboBox.currentIndex()][0])

        epsg = int(self.ellips_acronym[self.ellipsComboBox.currentIndex()][1])

        # Create point geometry..
        #point = tools.reproj(QgsPoint(som_coord_est, som_coord_nord),
        #                     tools.acronym_to_epsg(som_repres_plane), 4326)
        point = tools.reproj(QgsPoint(som_coord_est, som_coord_nord), epsg, 4326)

        # Create the feature..
        vertex = QgsFeature()
        vertex.setGeometry(QgsGeometry.fromPoint(point))
        vertex.setFields(self.l_vertex.pendingFields())
        vertex.setAttributes([QPyNullVariant(int),QPyNullVariant(int),
                              som_ge_createur, som_nature, som_prec_rattcht,
                              som_coord_est, som_coord_nord, som_repres_plane])

        self.l_vertex.addFeature(vertex)
        self.canvas.refresh()
        self.accept()

    def on_rejected(self):
        self.reject()
