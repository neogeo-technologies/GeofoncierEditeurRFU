# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Cut old limit
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the possibility to cut an old limit 
    *                at the point of a new vertex placed on this limit
    * First release: 2021-01-15
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QAbstractTableModel
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QBrush, QColor, QCursor
from qgis.core import QgsFeature, QgsGeometry, NULL
from qgis.gui import QgsMapToolIdentifyFeature, QgsMapToolIdentify

import os
import xml.etree.ElementTree as ElementTree
import operator
from functools import partial

from .global_vars import *
from .global_fnc import *
from .resize_dlg import ResizeDlg

gui_dlg_cut_oldlimit, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_cut_oldlimit.ui"))


class CutOldLimit(QDialog, gui_dlg_cut_oldlimit):
    
    def __init__(self, canvas, project, l_vertex, l_edge, parent=None):

        super(CutOldLimit, self).__init__(parent)
        self.setupUi(self)

        self.canvas = canvas
        self.project = project
        self.l_edge = l_edge
        self.l_vertex = l_vertex
        self.parent = parent
        
        self.sel_nw_vtx = None
                
        self.resize_dlg = ResizeDlg(self, "dlg_cut_oldlimit")
        self.resize_params = self.resize_dlg.load_dlgresize()
        self.resize_on = self.resize_params["dlg_cut_oldlimit"]
        
        self.valid_btn.clicked.connect(self.close)
        self.resize_btn.clicked.connect(self.resize_dlg.dlg_ch_resize)
        self.sel_oldlim_btn.clicked.connect(self.sel_oldlim)
        self.sel_nwvtx_btn.clicked.connect(self.sel_nwvtx)
        self.validop_btn.clicked.connect(self.validop)
        # Delete Widget on close event
        self.setAttribute(Qt.WA_DeleteOnClose)


    # Let the user select the RFU old limit to cut
    def sel_oldlim(self):
        # Selection in the canvas
        self.hide()
        self.l_edge.removeSelection()
        self.identify_oldlim = QgsMapToolIdentifyFeature(self.canvas, self.l_edge)
        self.identify_oldlim.setCursor(QCursor(Qt.PointingHandCursor))
        self.identify_oldlim.featureIdentified.connect(self.oldlim_identified)
        self.canvas.setMapTool(self.identify_oldlim)


    # Let the user select the new vertices used to cut the old lmit
    def sel_nwvtx(self):
        # Selection in the canvas
        self.hide()
        self.identify_nwvtx = MultiSelNwVtxTool(self.parent, self.canvas, self.l_vertex)
        # self.identify_nwvtx.setCursor(QCursor(Qt.PointingHandCursor))
        self.identify_nwvtx.selected_feats.connect(self.nwvtx_identified)
        self.canvas.setMapTool(self.identify_nwvtx)


    # Check of the limit after selection
    def oldlim_identified(self, feat):
        self.l_edge.selectByIds([feat.id()])
        self.canvas.unsetMapTool(self.identify_oldlim)
        # Check if the limit selected is an old RFU limit
        if feat[r"@id_arc"]:
            self.show()
        else:
            QMessageBox.warning(self, cutlim_notoldlim_msg[0], cutlim_notoldlim_msg[1])
            self.l_edge.removeSelection()
            self.sel_oldlim()    


    # Terminate the vertices selection
    def nwvtx_identified(self, lyr, feats):
        self.canvas.unsetMapTool(self.identify_nwvtx)
        self.show()      


    # Cut operation
    def validop(self):
        self.hide()
        # Transformations to obtain the WGS84 or the CC coordinates
        coords_tr_wgs, coords_tr_cc = crs_trans_params(self.canvas, self.project)
        # Message if no limit selected
        if len(self.l_edge.selectedFeatures()) == 0:
            QMessageBox.information(self, cutlim_nolim_msg[0], cutlim_nolim_msg[1])
            self.show()
        # Message if more than one limit selected
        elif len(self.l_edge.selectedFeatures()) > 1:
            QMessageBox.information(self, cutlim_toomuchlim_msg[0], cutlim_toomuchlim_msg[1])
            self.l_edge.removeSelection()
            self.show()
        # Message if no vertex selected
        elif len(self.l_vertex.selectedFeatures()) == 0:
            QMessageBox.information(self, cutlim_nonwvtx_msg[0], cutlim_nonwvtx_msg[1])
            self.show()
        # Do the job
        else:
            oldlim = self.l_edge.selectedFeatures()[0]
            # Find the att values
            lim_delim_pub = oldlim["lim_delimitation_publique"]
            lim_typologie_nature = oldlim["lim_typologie_nature"]
            oldlim_geom = oldlim.geometry()
            oldlim_geom_pl = oldlim_geom.asPolyline()
            start_lim_pt = oldlim_geom_pl[0]
            end_lim_pt = oldlim_geom_pl[-1]
            nw_pt_lst = []
            # Manage each new vertex
            for nwpt in self.l_vertex.selectedFeatures():
                # Find the creator
                ge_createur = nwpt["som_ge_createur"]
                nwpt_geom = nwpt.geometry()
                nwpt_geom_pt = nwpt_geom.asPoint()
                nw_pt_onlim = oldlim_geom.nearestPoint(nwpt_geom)
                dist_to_lim = dist_2_pts(coords_tr_cc.transform(nwpt_geom_pt), coords_tr_cc.transform(nw_pt_onlim.asPoint()))              
                dist_pr_st = dist_2_pts(coords_tr_cc.transform(start_lim_pt), coords_tr_cc.transform(nw_pt_onlim.asPoint()))
                dist_pr_en = dist_2_pts(coords_tr_cc.transform(end_lim_pt), coords_tr_cc.transform(nw_pt_onlim.asPoint()))
                # Check if the new vertex is out of the old limit
                if dist_pr_en == 0 or dist_pr_st == 0:
                    QMessageBox.information(self, cutlim_vtxout_msg[0], cutlim_vtxout_msg[1].format(nwpt.id()))
                else:
                    # Create the list of new points to use for the new lmits
                    nw_pt_lst.append([dist_pr_st, nwpt.id(), dist_to_lim, nwpt_geom_pt])
            # Sot the list of new points by their distance to the start vertex
            nw_pt_lst.sort()
            msg = ""
            if len(nw_pt_lst) > 0:
                # Create a message showing the distances, and asking to continue
                for nw_pt_info in nw_pt_lst:
                    msg += msg_dist.format(nw_pt_info[1], float(nw_pt_info[2]))
                q_ok = QMessageBox.question(self, cutlim_vtxdist_msg[0], cutlim_vtxdist_msg[1].format(msg), QMessageBox.Yes | QMessageBox.No)
                # The user continues
                if q_ok == QMessageBox.Yes:
                    for id, pt in enumerate(nw_pt_lst):
                        end_vtx = pt[3]
                        if id == 0:
                            st_vtx = start_lim_pt                            
                        line = QgsGeometry.fromPolylineXY([st_vtx, end_vtx])
                        st_vtx = pt[3]
                        nw_attvals = [NULL, NULL, ge_createur, lim_delim_pub, lim_typologie_nature]
                        # Create the feature
                        create_nw_feat(self.l_edge, line, nw_attvals)
                        # Case of the last limit to create
                        if id == (len(nw_pt_lst) -1):
                            line = QgsGeometry.fromPolylineXY([end_vtx, end_lim_pt])
                            create_nw_feat(self.l_edge, line, nw_attvals)
                    self.l_edge.deleteFeature(oldlim.id())
                    self.l_edge.removeSelection()
                    self.l_vertex.removeSelection()
                    QMessageBox.information(self, cutlim_end_msg[0], cutlim_end_msg[1])
                else:
                    self.show() 
            # No new limit to create
            else:
                QMessageBox.information(self, cutlim_noncre_msg[0], cutlim_noncre_msg[1])
                self.show()      


    def closeEvent(self, event):
        self.l_vertex.removeSelection()
        self.l_edge.removeSelection()
        self.close()
        

# MapTool to select several new vertices
class MultiSelNwVtxTool(QgsMapToolIdentify):

    selected_feats = pyqtSignal(QgsVectorLayer, list)

    def __init__(self, parent, canvas, layer):
        super(QgsMapToolIdentify, self).__init__(canvas)
        self.parent = parent
        self.canvas = canvas
        self.layer = layer
        self.cursor = QCursor(Qt.PointingHandCursor)
        self.setCursor(self.cursor)


    def canvasReleaseEvent(self, event):
        
        results = self.identify(event.x(), event.y(), self.LayerSelection , [self.layer], self.VectorLayer)
        # Stop the selection if right-click
        if event.button() == Qt.RightButton:
            self.selected_feats.emit(self.layer, self.layer.selectedFeatures())
        else:
            if len(results) > 0:
                for result in results:
                    feat = result.mFeature
                    # Check if it's a new vertex otherwise, not selected
                    if feat[r"@id_noeud"]:
                        QMessageBox.warning(self.parent, tr_vtxplt_notnwvtx_msg[0], tr_vtxplt_notnwvtx_msg[1])
                    else:
                        # Deselect if click on a selected object
                        if feat.id() in self.layer.selectedFeatureIds():
                            self.layer.deselect(feat.id())
                        else:
                            self.layer.select(feat.id())
            else:
                # Deselect all if click not on a point
                self.layer.removeSelection()
        
            
