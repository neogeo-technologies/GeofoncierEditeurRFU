# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Vertex creator
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the Vertex Creator
    * First release: 2015
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license 
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
                 typo_nature_som=[], auth_creator=[], tol_spt=0.0):

        super(VertexCreator, self).__init__(parent)
        self.setupUi(self)

        self.canvas = canvas
        self.project = project
        self.l_vertex = l_vertex
        self.user = user
        self.precision_class = precision_class
        self.ellips_acronym = ellips_acronym
        self.selected_ellips_acronym = selected_ellips_acronym
        self.typo_nature_som = typo_nature_som
        self.auth_creator = auth_creator
        self.tol_spt = tol_spt

        self.coordx_led.clear()
        self.coordy_led.clear()

        # fix_print_with_import
        print(ellips_acronym)

        for i, e in enumerate(self.ellips_acronym):
            self.ellips_cmb.addItem(e[2])
            if not selected_ellips_acronym:
                continue
            if selected_ellips_acronym == e[0]:
                self.ellips_cmb.setCurrentIndex(i)

        # Attribute: `som_precision_rattachement`
        for e in self.precision_class:
            self.precision_class_cmb.addItem(e[1])

        # Attribute: `som_typologie_nature`
        for e in self.typo_nature_som:
            self.typo_nat_cmb.addItem(e)

        # Attribute: `som_createur`
        for i, e in enumerate(self.auth_creator):
            self.createur_cmb.addItem("%s (%s)" % (e[1], e[0]))
            # Set current user as the creator by default..
            if user == e[0]:
                self.createur_cmb.setCurrentIndex(i)
        
        self.valid_btn.accepted.connect(self.on_accepted)
        self.valid_btn.rejected.connect(self.on_rejected)
        
        # Manage nature equals tyop_nature (by default)
        self.typo_nat_cmb.currentTextChanged.connect(self.nature_completion)
        # Manage delim_pub_chk text
        self.delim_pub_chk.stateChanged.connect(self.settext_delim_pub_chk)
        
        # Set typo_nature to Borne (by default)
        self.typo_nat_cmb.setCurrentText(dft_som_typo_nat)
        
    # Change the nature to apply the topologie_nature
    def nature_completion(self):
        self.nat_led.setText(self.typo_nat_cmb.currentText())
        
    # Change the text of the delim_pub checkbox
    def settext_delim_pub_chk(self):
        if self.delim_pub_chk.isChecked():
            self.delim_pub_chk.setText('oui')
        else:
            self.delim_pub_chk.setText('non')

    def on_accepted(self):

        # Check if coordinates are entered..
        if not self.coordx_led.text() or not self.coordy_led.text():
            css = "background-color: rgb(255, 189, 189);"
            self.coordx_led.setStyleSheet(css)
            self.coordy_led.setStyleSheet(css)
            return None

        # Set attributes
        som_ge_createur = self.auth_creator[self.createur_cmb.currentIndex()][0]
        som_typologie_nature = self.typo_nat_cmb.currentText()
        som_nature = self.nat_led.text()
        som_coord_est = float(self.coordx_led.text())
        som_coord_nord = float(self.coordy_led.text())
        
        som_repres_plane = self.ellips_acronym[self.ellips_cmb.currentIndex()][0]
        som_prec_rattcht = int(self.precision_class[self.precision_class_cmb.currentIndex()][0])
        # Transform the delim_pub checkbox into the correct value
        som_delim_pub = chkbox_to_truefalse(self.delim_pub_chk)

        epsg = int(self.ellips_acronym[self.ellips_cmb.currentIndex()][1])

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
            # Create the feature
            create_nw_feat( self.l_vertex, 
                            QgsGeometry.fromPointXY(nw_pt_wgs), 
                            [NULL, NULL, som_ge_createur, som_delim_pub, som_typologie_nature, som_nature, som_prec_rattcht, som_coord_est, som_coord_nord, som_repres_plane, 0.0, "false", id_ptintol]
                            )
            self.canvas.refresh()
        self.accept()
        
    def on_rejected(self):
        self.reject()
