# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Vertex creator
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the Vertex Creator
    * First release: 2015
    * Last release:  2019-08-19
    * Copyright:     (C) 2015 Géofoncier(R), (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""



from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, NULL

import os

from . import tools
from .global_vars import *
from .global_fnc import *

gui_dlg_vertex_creator, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_vertex_creator.ui"))


class VertexCreator(QDialog, gui_dlg_vertex_creator):

    def __init__(self, canvas, project, l_vertex, parent=None, user=None,
                 precision_class=[], ellips_acronym=[],
                 selected_ellips_acronym = None,
                 nature=[], auth_creator=[], tol_spt=0.0):

        super(VertexCreator, self).__init__(parent)
        self.setupUi(self)

        self.canvas = canvas
        self.project = project
        self.l_vertex = l_vertex
        self.user = user
        self.precision_class = precision_class
        self.ellips_acronym = ellips_acronym
        self.selected_ellips_acronym = selected_ellips_acronym
        self.nature = nature
        self.auth_creator = auth_creator
        self.tol_spt = tol_spt

        self.xLineEdit.clear()
        self.yLineEdit.clear()

        # fix_print_with_import
        print(ellips_acronym)

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
            css = "background-color: rgb(255, 189, 189);"
            self.xLineEdit.setStyleSheet(css)
            self.yLineEdit.setStyleSheet(css)
            return None

        # Set attributes..
        som_ge_createur = self.auth_creator[self.creatorComboBox.currentIndex()][0]
        som_nature = self.natureComboBox.currentText()
        som_coord_est = float(self.xLineEdit.text())
        som_coord_nord = float(self.yLineEdit.text())
        
        som_repres_plane = self.ellips_acronym[self.ellipsComboBox.currentIndex()][0]
        som_prec_rattcht = int(self.precision_class[self.precisionClassComboBox.currentIndex()][0])

        epsg = int(self.ellips_acronym[self.ellipsComboBox.currentIndex()][1])

        self.original_l_vtx = self.l_vertex
        # Transformations to obtain the WGS84 or the CC coordinates
        coords_trf_wgs, coords_trf_cc = crs_trans_params(self.canvas, self.project)
        nw_pt = QgsPointXY(som_coord_est, som_coord_nord)
        nw_pt_wgs = tools.reproj(nw_pt, epsg, 4326, self.project)
        # Check if the new vertex is in the tolerance of an existing vertex in the RFU
        to_create = True
        id_ptintol = NULL
        for vtx_feat in self.original_l_vtx.getFeatures() :
            vtx_feat_g = vtx_feat.geometry()
            vtx_tol = vtx_feat['som_tolerance']
            if vtx_feat_g.type() == QgsWkbTypes.PointGeometry :
                vtx_feat_pt = vtx_feat_g.asPoint()
                vtx_feat_pt_cc = coords_trf_cc.transform(vtx_feat_pt)
                pt_in_tol = find_near(vtx_feat_pt_cc, nw_pt, vtx_tol)
                if pt_in_tol[0]:
                    # Case of existing RFU point in the tolerance distance
                    if vtx_feat['@id_noeud']:
                        id_ptintol = vtx_feat['@id_noeud']
                        if pt_in_tol[1] > 0:
                            m_box = mbox_w_params(tl_pt_exst_rfu, txt_nwpt_exst_rfu, 
                                                    inftxt_nwpt_exst_rfu.format(
                                                                float(vtx_tol), id_ptintol))
                        # Case of strictly identical point
                        else:
                            to_create = False
                            m_box = mbox_w_params(tl_ptrfu_dbl, txt_nwpt_rfu_dbl, 
                                                    inftxt_nwpt_rfu_dbl.format(id_ptintol))
                    # Case of double point among new points
                    else:
                        to_create = False 
                        m_box = mbox_w_params(tl_nwpt_dbl, txt_nwpt_dbl, inftxt_nwpt_dbl)
                    m_box.exec_()
        # Creation of the RFU objects in the layers
        if to_create:
            # Create the feature..
            vertex = QgsFeature()
            vertex.setGeometry(QgsGeometry.fromPointXY(nw_pt_wgs))
            vertex.setFields(self.l_vertex.fields())
            vertex.setAttributes([NULL, NULL,
                                  som_ge_createur, som_nature, som_prec_rattcht,
                                  som_coord_est, som_coord_nord, som_repres_plane, 0.0, "false", id_ptintol])
            self.l_vertex.addFeature(vertex)
            self.canvas.refresh()
        self.accept()
        
    def on_rejected(self):
        self.reject()
