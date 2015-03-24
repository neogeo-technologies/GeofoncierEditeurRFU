#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os

from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QPyNullVariant
from PyQt4.QtGui import QDockWidget
from PyQt4.QtGui import QDialogButtonBox
from PyQt4.QtGui import QCursor
from qgis.core import QgsFeature
from qgis.core import QgsGeometry
from qgis.gui import QgsMapToolIdentifyFeature


gui_dckwdgt_edge_creator, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), r"gui/dckwdgt_edge_creator.ui"))


class EdgeCreator(QDockWidget, gui_dckwdgt_edge_creator):

    closed = pyqtSignal()

    def __init__(self, canvas, l_vertex, l_edge,
                 user=None, auth_creator=[], parent=None):

        super(EdgeCreator, self).__init__(parent)
        self.setupUi(self)

        # Delete Widget on close event..
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.save = False

        self.canvas = canvas
        self.l_edge = l_edge
        self.l_vertex = l_vertex
        self.user = user
        self.auth_creator = auth_creator

        self.vertices = self.l_vertex.getFeatures()
        self.vtx_start = None
        self.vtx_end = None
        self.selected_vertices = [None, None]

        self.edge = None

        for i, vertex in enumerate(self.vertices):

            self.startVertexComboBox.insertItem(i, str(vertex.id()))
            self.startVertexComboBox.setItemData(i, vertex, 32)

            self.endVertexComboBox.insertItem(i, str(vertex.id()))
            self.endVertexComboBox.setItemData(i, vertex, 32)

        # Attribute: `som_createur`
        for i, e in enumerate(self.auth_creator):
            self.creatorComboBox.addItem(u"%s (%s)" % (e[1], e[0]))
            if self.user == e[0]:
                self.creatorComboBox.setCurrentIndex(i)

        self.startVertextoolButton.clicked.connect(self.select_start_vertex_on_canvas)
        self.endVertextoolButton.clicked.connect(self.select_end_vertex_on_canvas)

        self.startVertexComboBox.highlighted.connect(self.on_vtx_start_pressed)
        self.endVertexComboBox.highlighted.connect(self.on_vtx_end_pressed)
        self.startVertexComboBox.currentIndexChanged.connect(self.on_vtx_start_pressed)
        self.endVertexComboBox.currentIndexChanged.connect(self.on_vtx_end_pressed)

        self.startVertexComboBox.highlighted.connect(self.create_edge)
        self.endVertexComboBox.highlighted.connect(self.create_edge)
        self.startVertexComboBox.currentIndexChanged.connect(self.create_edge)
        self.endVertexComboBox.currentIndexChanged.connect(self.create_edge)

        self.buttonBox.accepted.connect(self.on_accepted)
        self.buttonBox.rejected.connect(self.on_rejected)
        self.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(self.on_reset)

    def closeEvent(self, event):
        if not self.save:
            self.on_rejected()

    def select_start_vertex_on_canvas(self):

        self.identify_start_vertex = QgsMapToolIdentifyFeature(self.canvas, self.l_vertex)
        self.identify_start_vertex.setCursor(QCursor(Qt.PointingHandCursor))
        self.identify_start_vertex.featureIdentified.connect(self.on_start_vertex_identified)
        self.canvas.setMapTool(self.identify_start_vertex)

    def select_end_vertex_on_canvas(self):

        self.identify_end_vertex = QgsMapToolIdentifyFeature(self.canvas, self.l_vertex)
        self.identify_end_vertex.setCursor(QCursor(Qt.PointingHandCursor))
        self.identify_end_vertex.featureIdentified.connect(self.on_end_vertex_identified)
        self.canvas.setMapTool(self.identify_end_vertex)

    def on_start_vertex_identified(self, feature):

        cb = self.startVertexComboBox
        items = [cb.itemText(i) for i in range(cb.count())]
        for i, e in enumerate(items):
            if int(feature.id()) == int(e):
                cb.setCurrentIndex(i)

    def on_end_vertex_identified(self, feature):

        cb = self.endVertexComboBox
        items = [cb.itemText(i) for i in range(cb.count())]
        for i, e in enumerate(items):
            if int(feature.id()) == int(e):
                cb.setCurrentIndex(i)

    def on_vtx_start_pressed(self, idx):

        self.vtx_start = self.startVertexComboBox.itemData(idx, 32)
        self.select_vertices(self.vtx_start, 0)

        self.endVertexComboBox.setEnabled(True)
        self.endVertextoolButton.setEnabled(True)

    def on_vtx_end_pressed(self, idx):

        self.vtx_end = self.endVertexComboBox.itemData(idx, 32)
        self.select_vertices(self.vtx_end, 1)

        self.creatorComboBox.setEnabled(True)

    def select_vertices(self, feature, i):
        if feature:
            self.selected_vertices[i] = feature.id()
        else:
            self.selected_vertices[i] = None
        self.l_vertex.setSelectedFeatures(self.selected_vertices)

    def unselect_vertices(self):
        self.l_vertex.setSelectedFeatures([])

    def create_edge(self):

        # If edge already exists, delete it..
        if self.edge:
            self.l_edge.deleteFeature(self.edge.id())

        # Two vertices are needed..
        if not self.vtx_start or not self.vtx_end:
            return self.canvas.refresh()

        # Two DIFFERENT vertices..
        if self.vtx_start == self.vtx_end:
            return self.canvas.refresh()

        # Create line geometry..
        line = QgsGeometry.fromPolyline([self.vtx_start.geometry().asPoint(),
                                         self.vtx_end.geometry().asPoint()])

        # Create the feature..
        self.edge = QgsFeature()
        self.edge.setGeometry(line)
        self.edge.setFields(self.l_edge.pendingFields())
        self.edge.setAttributes(
                [QPyNullVariant(int), QPyNullVariant(int), QPyNullVariant(int)])

        # Add feature to layer..
        self.l_edge.addFeature(self.edge)
        self.canvas.refresh()

    def on_accepted(self):

        if not self.edge:
            return False

        self.lim_ge_createur = self.auth_creator[self.creatorComboBox.currentIndex()][0]
        self.edge.setAttributes(
                [QPyNullVariant(int), QPyNullVariant(int), self.lim_ge_createur])
        self.l_edge.updateFeature(self.edge)
        self.canvas.refresh()
        self.save = True
        self.close()

    def on_rejected(self):

        # Do not save the feature..
        if self.edge:
            self.l_edge.deleteFeature(self.edge.id())

        self.unselect_vertices()
        self.canvas.refresh()
        self.close()

    def on_reset(self):

        self.startVertexComboBox.setCurrentIndex(0)
        # self.startVertexComboBox.setEnabled(True)
        # self.startVertexLabel.setEnabled(True)

        self.endVertexComboBox.setCurrentIndex(0)
        self.endVertexComboBox.setEnabled(False)
        self.endVertexLabel.setEnabled(False)
        self.endVertextoolButton.setEnabled(False)

        for i, e in enumerate(self.auth_creator):
            if self.user == e[0]:
                self.creatorComboBox.setCurrentIndex(i)
        self.creatorComboBox.setEnabled(False)
        self.creatorLabel.setEnabled(False)

        self.unselect_vertices()
        self.canvas.refresh()
