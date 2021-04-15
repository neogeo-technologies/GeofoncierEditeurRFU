# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Show ptplots
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the possibility to show the 
    *                list of plots associated to  specific vertex
    * First release: 2019-07-25
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
from qgis.gui import QgsMapToolIdentifyFeature

import os
import xml.etree.ElementTree as ElementTree
import operator
from functools import partial

from .global_vars import *
from .global_fnc import *
from .resize_dlg import ResizeDlg

gui_dlg_transfo_pttoplot, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_transfo_pttoplot.ui"))


class TransfoPtToPlot(QDialog, gui_dlg_transfo_pttoplot):
    
    def __init__(self, canvas, project, l_vertex, l_edge, parent=None):

        super(TransfoPtToPlot, self).__init__(parent)
        self.setupUi(self)

        self.canvas = canvas
        self.project = project
        self.l_edge = l_edge
        self.l_vertex = l_vertex
        
        self.sel_nw_vtx = None
                
        self.resize_dlg = ResizeDlg(self, "dlg_transfo_pt_to_plots")
        self.resize_params = self.resize_dlg.load_dlgresize()
        self.resize_on = self.resize_params["dlg_transfo_pt_to_plots"]
        
        self.buttValid.clicked.connect(self.close)
        self.buttResize.clicked.connect(self.resize_dlg.dlg_ch_resize)
        self.selrfuvtxnearButt.clicked.connect(self.sel_nwvtxnear_rfu)
        self.nearvtxvalButt.clicked.connect(self.nwvtx_valid)
        self.selnwvxtButt.clicked.connect(self.sel_nwvtxfar)
        self.selrfuvtxfarButt.clicked.connect(self.sel_rfuvtxfar)
        self.nearvtxTbv.clicked.connect(self.tbv_sel)
        
        # Delete Widget on close event
        self.setAttribute(Qt.WA_DeleteOnClose)
 
    # Zoom to 2 new + RFU vertices if a line is selected in the tableview
    def tbv_sel(self):
        # Find the selected cell (considering only the first selected cell)
        idx = self.nearvtxTbv.selectedIndexes()[0].row()
        # Find the new vertex feature and the near RFU vertex feature
        self.sel_nw_vtx = self.nr_feats[idx]
        id_rfu_vtx = self.nr_feats[idx]["point_rfu_proche"]
        rfu_vtx = feats_by_cond(self.l_vertex, r"@id_noeud", id_rfu_vtx)[0]
        # Zoom to the 2 features
        self.canvas.zoomToFeatureIds(self.l_vertex, [self.sel_nw_vtx.id(), rfu_vtx.id()])

    # Let the user select the new vertex to transform into a plot
    def sel_nwvtxfar(self):
        # Selection in the canvas
        self.hide()
        self.identify_nwvtxfar_vtx = QgsMapToolIdentifyFeature(self.canvas, self.l_vertex)
        self.identify_nwvtxfar_vtx.setCursor(QCursor(Qt.PointingHandCursor))
        self.identify_nwvtxfar_vtx.featureIdentified.connect(self.far_nwvtx_identified)
        self.canvas.setMapTool(self.identify_nwvtxfar_vtx)

    def far_nwvtx_identified(self, feat):
        self.l_vertex.selectByIds([feat.id()])
        # Check if the point selected is a new vertex
        if not feat[r"@id_noeud"]:
            self.sel_nw_vtx = feat
            self.canvas.unsetMapTool(self.identify_nwvtxfar_vtx)
            self.dlg_show()
        else:
            QMessageBox.warning(self, tr_vtxplt_notnwvtx_msg[0], tr_vtxplt_notnwvtx_msg[1])
       
    
    # Let the user select the RFU vertex to use with the far new vertex
    def sel_rfuvtxfar(self):
        # Selection in the canvas
        if self.sel_nw_vtx:
            self.hide()
            self.identify_rfuvtxfar_vtx = QgsMapToolIdentifyFeature(self.canvas, self.l_vertex)
            self.identify_rfuvtxfar_vtx.setCursor(QCursor(Qt.PointingHandCursor))
            self.identify_rfuvtxfar_vtx.featureIdentified.connect(partial(self.rfu_vtx_identified, "far"))
            self.canvas.setMapTool(self.identify_rfuvtxfar_vtx)
        # Message if no line selected in the tableview
        else:
            QMessageBox.warning(self, tr_vtxplt_sel_nonwvtxsel_msg[0], tr_vtxplt_sel_nonwvtxsel_msg[1])  

    # Let the user select the RFU vertex near the new vertex
    def sel_nwvtxnear_rfu(self):
        # Selection in the canvas
        if self.sel_nw_vtx:
            self.hide()
            self.identify_rfu_vtx = QgsMapToolIdentifyFeature(self.canvas, self.l_vertex)
            self.identify_rfu_vtx.setCursor(QCursor(Qt.PointingHandCursor))
            self.identify_rfu_vtx.featureIdentified.connect(partial(self.rfu_vtx_identified, "near"))
            self.canvas.setMapTool(self.identify_rfu_vtx)
        # Message if no line selected in the tablview
        else:
            QMessageBox.warning(self, tr_vtxplt_sel_nolinesel_msg[0], tr_vtxplt_sel_nolinesel_msg[1])
        
    def rfu_vtx_identified(self, vtx_type, feat):
        self.vtx_type = vtx_type
        self.l_vertex.selectByIds([feat.id()])
        if self.vtx_type == "near":
            self.canvas.unsetMapTool(self.identify_rfu_vtx)
        else:
            self.canvas.unsetMapTool(self.identify_rfuvtxfar_vtx)
        # Check if the point selected is a RFU vertex
        if feat[r"@id_noeud"]:
            id_node = feat[r"@id_noeud"]
            # Tolerance in cm
            tol = feat[r"som_tolerance"]*100
            nw_coord_e = self.sel_nw_vtx["som_coord_est"]
            nw_coord_n = self.sel_nw_vtx["som_coord_nord"]
            nw_rep_plane = self.sel_nw_vtx["som_representation_plane"]
            nw_pt_cc = QgsPointXY(self.sel_nw_vtx["som_coord_est"], self.sel_nw_vtx["som_coord_nord"])
            rfu_pt_cc = QgsPointXY(feat["som_coord_est"], feat["som_coord_nord"])
            # Distance between the 2 points in cm
            dist_vtx = dist_2_pts(nw_pt_cc, rfu_pt_cc)*100
            if dist_vtx < tol:
                self.vtx_type = "near"
            # Check if the 2 points have the same som_representation_plane
            # Otherwise, cancel the process
            if nw_rep_plane == feat["som_representation_plane"]:
                if self.vtx_type == "near":
                    tl_msg = tr_vtxplt_confirm_msg[0]
                    txt_msg = tr_vtxplt_confirm_msg[1].format(nw_coord_e, nw_coord_n, id_node)
                else:
                    tl_msg = tr_vtxplt_attest_msg[0]
                    txt_msg = tr_vtxplt_attest_msg[1].format(nw_coord_e, nw_coord_n, id_node, dist_vtx, tol)
                confirm = QMessageBox.question( self, tl_msg, txt_msg, 
                                                QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    nw_vals = {}
                    for att in tr_toplot_atts:
                        id_att = self.l_vertex.fields().indexFromName(att)
                        nw_vals[id_att] = self.sel_nw_vtx[att]
                    # Change the atteste_qualite value
                    if self.vtx_type == "far":
                        id_att = self.l_vertex.fields().indexFromName("attestation_qualite")
                        nw_vals[id_att] = "true"
                    self.l_vertex.changeAttributeValues(feat.id(), nw_vals)
                    self.l_vertex.deleteFeature(self.sel_nw_vtx.id())
                    self.tr_edges(self.sel_nw_vtx.geometry(), feat.geometry())
                    self.canvas.refresh()
                    QMessageBox.information(
                                self, 
                                tr_vtxplot_transfok_msg[0], 
                                tr_vtxplot_transfok_msg[1].format(nw_coord_e, nw_coord_n, id_node))
                # Process canceled by the user    
                else:
                    QMessageBox.information(self, tr_vtxplt_canceld_msg[0], tr_vtxplt_canceld_msg[1])
            # Case of no same som_representation_plane
            else:
                QMessageBox.warning(self, tr_vtxplot_nosamerp_msg[0], tr_vtxplot_nosamerp_msg[1])
            self.nearvtxTbv.clearSelection()
            self.sel_nw_vtx = None
            # Deselect point
            self.l_vertex.selectByIds([])
            self.dlg_show()
        else:
            QMessageBox.warning(self, tr_vtxplt_notrfuvtx_msg[0], tr_vtxplt_notrfuvtx_msg[1])
            if self.vtx_type == "near":
                self.sel_nwvtxnear_rfu()
            else:
                self.sel_rfuvtxfar()
        
    # Move edges if they are linked to a new vertex transformed into plot
    def tr_edges(self, old_geom, nw_geom):
        # Transformations to obtain the WGS84 or the CC coordinates
        coords_tr_wgs, coords_tr_cc = crs_trans_params(self.canvas, self.project)
        old_geom_pt = old_geom.asPoint()
        nw_geom_pt = nw_geom.asPoint()
        old_geom_cc = coords_tr_cc.transform(old_geom_pt)
        # Process only new edges
        nw_edges = feats_by_cond(self.l_edge, "@id_arc", NULL)
        if len(nw_edges) > 0:
            for edge_ft in nw_edges:
                ch_geom = False
                edge_ft_line = edge_ft.geometry().asPolyline()
                start_pt = edge_ft_line[0]
                end_pt = edge_ft_line[-1]
                # Comparison done on cc coordinates
                start_pt_cc = coords_tr_cc.transform(start_pt)
                end_pt_cc = coords_tr_cc.transform(end_pt)  
                # Case of start point to move
                if check_identical_pts(old_geom_cc, start_pt_cc, 2):
                    self.l_edge.moveVertex(nw_geom_pt.x(), nw_geom_pt.y(), edge_ft.id(), 0)
                    nw_line_g = QgsGeometry.fromPolylineXY([nw_geom_pt, end_pt])
                    ch_geom = True
                # Case of end point to move
                if check_identical_pts(old_geom_cc, end_pt_cc, 2):
                    self.l_edge.moveVertex(nw_geom_pt.x(), nw_geom_pt.y(), edge_ft.id(), 1)
                    nw_line_g = QgsGeometry.fromPolylineXY([start_pt, nw_geom_pt])
                    ch_geom = True
                # Check if new line is the same as an existing edge_ft
                # In this case, delete the new line
                if ch_geom:
                    for old_edge_ft in self.l_edge.getFeatures():
                        if old_edge_ft.id() != edge_ft.id() and \
                            check_identical_lines(old_edge_ft.geometry().asPolyline(), nw_line_g.asPolyline(), 12):
                            self.l_edge.deleteFeature(edge_ft.id())
    
    
    # Let the user valid the new vertex
    def nwvtx_valid(self):       
        # Reset the point_rfu_proche field
        if self.sel_nw_vtx:
            self.l_vertex.changeAttributeValue(self.sel_nw_vtx.id(), 10, NULL)
            # self.l_vertex.commitChanges()
            self.canvas.refresh()
            QMessageBox.information(self, tr_vtxplt_valid_msg[0], tr_vtxplt_valid_msg[1].format(self.sel_nw_vtx["som_coord_est"], self.sel_nw_vtx["som_coord_nord"]))
            self.nearvtxTbv.clearSelection()
            self.sel_nw_vtx = None
            self.hide()
            self.dlg_show()
        # Message if no line selected in the tablview
        else:
            QMessageBox.warning(self, tr_vtxplt_nolinesel_msg[0], tr_vtxplt_nolinesel_msg[1])

    
    # Launch the dlg appearence
    def dlg_show(self):
                                 
        self.nr_feats = []
        # Create the tableview
        self.tr_vtxtbl_data = []
        tr_vtxtbl_hd = []
        # Build the header
        for fld_name in tr_vtx_atts:
            tr_vtxtbl_hd.append(fld_name)
        # Build the contents
        nb_rows = 0
        for obj in self.l_vertex.getFeatures():
            if obj['point_rfu_proche']:
                tr_vtxtbl_row = []
                for fld_name in tr_vtx_atts:
                    tr_vtxtbl_row.append(str(obj[fld_name]))
                self.tr_vtxtbl_data.append(tr_vtxtbl_row)
                self.nr_feats.append(obj)
                nb_rows += 1
        if nb_rows != 0:
            tr_vtxtbl_model=MyTableModel(self, self.tr_vtxtbl_data, tr_vtxtbl_hd)
            # Populate data in the tableview
            self.nearvtxTbv.setModel(tr_vtxtbl_model)
            self.height_tbv = 0
            self.width_tbv = 0
            # Set column width to fit contents
            self.nearvtxTbv.resizeColumnsToContents()
            # Increase a little bit the width of the columns
            for id_col, val_col in enumerate(tr_vtxtbl_hd):
                nw_size = self.nearvtxTbv.columnWidth(id_col) + 5
                self.nearvtxTbv.setColumnWidth(id_col, nw_size)
                self.width_tbv += nw_size
            # Set row height
            self.nearvtxTbv.resizeRowsToContents()
            self.height_tbv = (self.nearvtxTbv.rowHeight(0)) * (nb_rows+1)
            self.width_tbv += 45
            self.height_tbv += 330
            self.resize_dlg.wtbv = self.width_tbv
            self.resize_dlg.htbv = self.height_tbv
            # Hide vertical header
            vh = self.nearvtxTbv.verticalHeader()
            vh.setVisible(False)
        else:
            self.nearvtxGp.hide()
            self.width_tbv = dlg_transfo_pt_to_plots_sw
            self.height_tbv = 176
            self.resize_dlg.wtbv = self.width_tbv
            self.resize_dlg.htbv = self.height_tbv
        if self.resize_on:
            self.resize_dlg.dlg_auto_resize()
        self.show()
        
   
    def to_close(self):
        self.close()
        
            
# Creation of the model for a TableView
# Example of the mylist to pass:
# mylist = [['00','01','02'],
#           ['10','11','12'],
#           ['20','21','22']]
class MyTableModel(QAbstractTableModel):

    layoutAboutToBeChanged = pyqtSignal()
    layoutChanged = pyqtSignal()
    def __init__(self, parent, mylist, header, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.mylist = mylist
        self.header = header
    def rowCount(self, parent):
        return len(self.mylist)
    def columnCount(self, parent):
        return len(self.mylist[0])
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    # No sorting allowed for this tableview
    # def sort(self, col, order):
        # """sort table by given column number col"""
        # self.layoutAboutToBeChanged.emit()
        # self.mylist = sorted(self.mylist,
            # key=operator.itemgetter(col))
        # if order == Qt.DescendingOrder:
            # self.mylist.reverse()
        # self.layoutChanged.emit()
