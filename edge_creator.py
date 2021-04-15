# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Edge creator
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the Edge Creator
    * First release: 2015
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license 
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtWidgets import QDockWidget, QDialogButtonBox 
from qgis.PyQt.QtGui import QCursor
from qgis.core import Qgis, QgsFeature, QgsGeometry, NULL
from qgis.gui import QgsMapToolIdentifyFeature

import os

from .global_vars import *
from .global_fnc import *


gui_dckwdgt_edge_creator, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), r"gui/dckwdgt_edge_creator.ui"))


class EdgeCreator(QDockWidget, gui_dckwdgt_edge_creator):

    def __init__(self, iface, canvas, l_vertex, l_edge, typo_nature_lim=[],
                 user=None, auth_creator=[], parent=None):

        super(EdgeCreator, self).__init__(parent)
        self.setupUi(self)

        # Delete Widget on close event..
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.save = False

        self.iface = iface
        self.canvas = canvas
        self.l_edge = l_edge
        self.l_vertex = l_vertex
        self.typo_nature_lim = typo_nature_lim
        self.user = user
        self.auth_creator = auth_creator

        self.vertices = self.l_vertex.getFeatures()
        self.vtx_start = None
        self.vtx_end = None
        self.selected_vertices = [None, None]

        self.edge = None       

        for i, vertex in enumerate(self.vertices):

            self.start_vtx_cmb.insertItem(i, str(vertex.id()))
            self.start_vtx_cmb.setItemData(i, vertex, 32)
            self.start_vtx_cmb.setCurrentIndex(-1)

            self.end_vtx_cmb.insertItem(i, str(vertex.id()))
            self.end_vtx_cmb.setItemData(i, vertex, 32)
            self.end_vtx_cmb.setCurrentIndex(-1)

        # Attribute: `lim_typologie_nature`
        for e in self.typo_nature_lim:
            self.typo_nat_cmb.addItem(e)
        
        # Attribute: `som_createur`
        for i, e in enumerate(self.auth_creator):
            self.createur_cmb.addItem(u"%s (%s)" % (e[1], e[0]))
            if self.user == e[0]:
                self.createur_cmb.setCurrentIndex(i)

        self.start_vtx_tb.clicked.connect(self.select_start_vertex_on_canvas)
        self.end_vtx_tb.clicked.connect(self.select_end_vertex_on_canvas)

        self.start_vtx_cmb.highlighted.connect(self.on_vtx_start_pressed)
        self.end_vtx_cmb.highlighted.connect(self.on_vtx_end_pressed)
        self.start_vtx_cmb.currentIndexChanged.connect(self.on_vtx_start_pressed)
        self.end_vtx_cmb.currentIndexChanged.connect(self.on_vtx_end_pressed)

        self.start_vtx_cmb.highlighted.connect(self.create_edge)
        self.end_vtx_cmb.highlighted.connect(self.create_edge)
        self.start_vtx_cmb.currentIndexChanged.connect(self.create_edge)
        self.end_vtx_cmb.currentIndexChanged.connect(self.create_edge)
        
        # Manage delim_pub_chk text
        self.delim_pub_chk.stateChanged.connect(self.settext_delim_pub_chk)

        self.valid_btn.accepted.connect(self.on_accepted)
        self.valid_btn.rejected.connect(self.on_rejected)
        self.valid_btn.button(QDialogButtonBox.Reset).clicked.connect(self.on_reset)
        
        # Set typo_nature to Limite privée (by default)
        self.typo_nat_cmb.setCurrentText('Limite privée')
        
        # Prompt message
        self.iface.messageBar().pushMessage(
            edge_crea_txt[0], edge_crea_txt[1],
            Qgis.Info, duration=10)
        
        # Launch the choice of first vertex
        self.start_vtx_tb.click()
        
        
    # Change the text of the delim_pub checkbox
    def settext_delim_pub_chk(self):
        if self.delim_pub_chk.isChecked():
            self.delim_pub_chk.setText('oui')
        else:
            self.delim_pub_chk.setText('non')


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

        cb = self.start_vtx_cmb
        items = [cb.itemText(i) for i in range(cb.count())]
        for i, e in enumerate(items):
            if int(feature.id()) == int(e):
                cb.setCurrentIndex(i)
        self.end_vtx_tb.click()


    def on_end_vertex_identified(self, feature):

        cb = self.end_vtx_cmb
        items = [cb.itemText(i) for i in range(cb.count())]
        for i, e in enumerate(items):
            if int(feature.id()) == int(e):
                cb.setCurrentIndex(i)


    def on_vtx_start_pressed(self, idx):

        self.vtx_start = self.start_vtx_cmb.itemData(idx, 32)
        self.select_vertices(self.vtx_start, 0)

        self.end_vtx_cmb.setEnabled(True)
        self.end_vtx_tb.setEnabled(True)


    def on_vtx_end_pressed(self, idx):

        self.vtx_end = self.end_vtx_cmb.itemData(idx, 32)
        self.select_vertices(self.vtx_end, 1)

        self.createur_cmb.setEnabled(True)


    def select_vertices(self, feature, i):
        if feature:
            self.selected_vertices[i] = feature.id()
        else:
            self.selected_vertices[i] = None

        if not None in self.selected_vertices:
            self.l_vertex.selectByIds(self.selected_vertices)
        elif feature:
            self.l_vertex.selectByIds([feature.id()])


    def unselect_vertices(self):
        self.l_vertex.selectByIds([])


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
            
        self.lim_ge_createur = self.auth_creator[self.createur_cmb.currentIndex()][0]
        lim_typologie_nature = self.typo_nat_cmb.currentText()
        
        # Create line geometry..
        line = QgsGeometry.fromPolylineXY([self.vtx_start.geometry().asPoint(),
                                         self.vtx_end.geometry().asPoint()])
        self.original_l_edge = self.l_edge
        # Check if the lines intersects
        # Transform the delim_pub checkbox into the correct value
        lim_delim_pub = chkbox_to_truefalse(self.delim_pub_chk)
        to_create = check_limit_cross(line, self.original_l_edge, self.lim_ge_createur, lim_delim_pub, lim_typologie_nature, self.canvas, False)
        # Creation of the RFU objects in the layer
        if to_create:
            # Create the feature..
            self.edge = create_nw_feat(self.l_edge, line, [NULL, NULL, NULL, NULL, NULL])
        else:
            self.on_reset()
        self.canvas.refresh()


    def on_accepted(self):

        if not self.edge:
            return False

        self.lim_ge_createur = self.auth_creator[self.createur_cmb.currentIndex()][0]
        
        # Transform the delim_pub checkbox into the correct value
        lim_delim_pub = chkbox_to_truefalse(self.delim_pub_chk)
            
        lim_typologie_nature = self.typo_nat_cmb.currentText()
        
        self.edge.setAttributes(
                [NULL, NULL, self.lim_ge_createur, lim_delim_pub, lim_typologie_nature])
        self.l_edge.updateFeature(self.edge)
        self.l_vertex.removeSelection()
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

        self.start_vtx_cmb.setCurrentIndex(-1)

        self.end_vtx_cmb.setCurrentIndex(-1)
        self.end_vtx_cmb.setEnabled(False)
        self.end_vtx_lab.setEnabled(False)
        self.end_vtx_tb.setEnabled(False)

        for i, e in enumerate(self.auth_creator):
            if self.user == e[0]:
                self.createur_cmb.setCurrentIndex(i)
        self.createur_cmb.setEnabled(False)
        self.createur_lab.setEnabled(False)

        self.unselect_vertices()
        self.canvas.refresh()
        self.start_vtx_tb.click()
