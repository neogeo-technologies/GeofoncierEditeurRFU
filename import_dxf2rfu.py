# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Import DXF2RFU
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the possibility to import a DXF file
    *                and to structure it for the RFU.
    * First release: 2017-01-27
    * Last release:  2019-08-19
    * Copyright:     (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal, QSize
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QMessageBox, QFileDialog, QLabel, QComboBox, QLineEdit,
                                    QSizePolicy, QSpacerItem, QWidget, QDialog)
from qgis.core import QgsPointXY, QgsWkbTypes, QgsFeature, QgsGeometry, NULL

import os
import math
import json
import codecs

from . import sgmdxfparser
from .global_vars import * 
from .global_fnc import *

gui_dlg_dxf2rfu, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_paramdxf2rfu.ui"))


class ImportDxf2Rfu:
    
    def __init__(self, iface, canvas, project, l_vertex, l_edge,
                 user=None, auth_creator=[], parent=None,
                 precision_class=[], ellips_acronym=[],
                 selected_ellips_acronym=None,
                 nature=[],
                 tol_spt=0.0):
        
        self.iface = iface
        self.canvas = canvas
        self.project = project
        self.l_edge = l_edge
        self.l_vertex = l_vertex
        self.user = user
        self.auth_creator = auth_creator
        self.precision_class = precision_class
        self.nature = nature
        self.tol_spt = tol_spt
        self.cc = selected_ellips_acronym
        self.edge = None
        
    # Import DXF file
    def importFile(self):
        existing_pts = []
        self.original_l_vtx = self.l_vertex
        self.original_l_edge = self.l_edge
        dwg_file = QFileDialog.getOpenFileName (
                    None,
                    tl_dxf_choice,
                    os.path.expanduser("~"),
                    "DXF (*.dxf)"
                    )[0]
        if not dwg_file:
            QMessageBox.information(self.iface.mainWindow(), 
                tl_imp_canc, 
                txt_dxfimp_canc)
            return None
        else:
            # Read the DXF file
            dwg = sgmdxfparser.readfile(dwg_file)
            self.dwg_lyrs = dwg.layers
            self.dwg_blocks = dwg.blocks
            self.dwg_ents = list(dwg.modelspace())
            # Prepare the parameters window
            self.nw_param_dxf2rfu = ParamDxf2Rfu(self.dwg_lyrs, self.dwg_blocks, self.nature, self.precision_class)
            # Capture the dic of parameters when closing the dlg window
            self.nw_param_dxf2rfu.send_nw_params.connect(self.dxfOkParam) 
            # Modal window
            self.nw_param_dxf2rfu.setWindowModality(Qt.ApplicationModal)
            # Show the parameters window
            self.nw_param_dxf2rfu.show()
            
    # Launch the process of creation once the param window is validated
    def dxfOkParam(self, dic_param):
        self.nw_params = dic_param
        idx_prec = 1
        # Create the list of all natures
        nat_lst = []
        for k in list(self.nw_params.keys()):
            nat_lst.append(k)
        # Determine the precision class attribute
        for (idx, prec_val) in enumerate(self.precision_class):
            if self.precision_class[idx][1] == self.nw_params["precClass"]:
                idx_prec = idx
        idx_prec = int(self.precision_class[idx_prec][0])
        # Transformations to obtain the WGS84 or the CC coordinates
        coords_tr_wgs, coords_tr_cc = crs_trans_params(self.canvas, self.project)
        # Creation of the vertices
        elim_pts = []
        self.iface.setActiveLayer(self.l_edge)
        self.iface.setActiveLayer(self.l_vertex)
        vtx_blk_ents = [entity for entity in self.dwg_ents if entity.layer == self.nw_params["vtxLyr"] and entity.dxftype == "INSERT"]
        for pt_type in nat_lst:
            if self.nw_params[pt_type] == all_blks:
                vtx_curtypeblks = vtx_blk_ents
            else:
                vtx_curtypeblks = [entity for entity in vtx_blk_ents if entity.name == self.nw_params[pt_type]]
            for blk in vtx_curtypeblks:
                blk_pt = blk.insert
                nw_pt = QgsPointXY(float(blk_pt[0]), float(blk_pt[1]))
                nw_pt_wgs = coords_tr_wgs.transform(nw_pt)
                # Check if the new vertex is in the tolerance of an existing vertex in the RFU
                to_create = True
                id_ptintol = NULL
                for vtx_feat in self.original_l_vtx.getFeatures():
                    vtx_feat_g = vtx_feat.geometry()
                    vtx_tol = vtx_feat['som_tolerance']
                    if vtx_feat_g.type() == QgsWkbTypes.PointGeometry:
                        vtx_feat_pt = vtx_feat_g.asPoint()
                        vtx_feat_pt_cc = coords_tr_cc.transform(vtx_feat_pt)
                        # if find_near(vtx_feat_pt_cc, nw_pt, self.tol_spt):
                        pt_in_tol = find_near(vtx_feat_pt_cc, nw_pt, vtx_tol)
                        if pt_in_tol[0]:
                            # Case of existing RFU point in the tolerance distance
                            if vtx_feat['@id_noeud']:
                                id_ptintol = vtx_feat['@id_noeud']
                                if pt_in_tol[1] > 0:
                                    m_box = mbox_w_params(tl_pt_exst_rfu, txt_pt_exst_rfu, 
                                                            inftxt_pt_exst_rfu.format(nw_pt.x(), nw_pt.y(),
                                                            float(vtx_tol), id_ptintol))
                                # Case of strictly identical point
                                else:
                                    elim_dbpt = []
                                    elim_dbpt.append(nw_pt)
                                    elim_dbpt.append(vtx_feat_pt_cc)
                                    elim_pts.append(elim_dbpt)
                                    to_create = False
                                    m_box = mbox_w_params(tl_ptrfu_dbl, txt_ptrfu_dbl, 
                                                            inftxt_ptrfu_dbl.format(nw_pt.x(), nw_pt.y(), id_ptintol))
                            # Case of double point in the file imported
                            else:
                                m_box = mbox_w_params(tl_pt_dbl, txt_pt_dbl,
                                                        inftxt_pt_dbl.format(nw_pt.x(), nw_pt.y()))
                                # Add the list of new point eliminated and corresponding point 
                                # in the RFU to the list of eliminated points 
                                # (list of 2 point lists)
                                elim_dbpt = []
                                elim_dbpt.append(nw_pt)
                                elim_dbpt.append(vtx_feat_pt_cc)
                                elim_pts.append(elim_dbpt)
                                to_create = False
                            m_box.exec_()
                # Creation of the RFU objects in the layers
                if to_create:
                    vertex = QgsFeature()
                    vertex.setGeometry(QgsGeometry.fromPointXY(nw_pt_wgs))
                    vertex.setFields(self.l_vertex.fields())
                    vertex.setAttributes([NULL, NULL,
                                            self.user, pt_type, idx_prec, float("{0:.02f}".format(nw_pt.x())), float("{0:.02f}".format(nw_pt.y())), self.cc, 0.0, "false", id_ptintol])
                    # Add feature to the layer
                    self.l_vertex.addFeature(vertex)
        # Creation of the limits
        self.iface.setActiveLayer(self.l_vertex)
        self.iface.setActiveLayer(self.l_edge)
        edge_ents = [entity for entity in self.dwg_ents if entity.layer == self.nw_params["edgesLyr"] and \
                        (entity.dxftype == "LWPOLYLINE" or entity.dxftype == "LINE")]
        for lwp_ent in edge_ents:
            lwp_ent_pts = []
            if lwp_ent.dxftype == "LWPOLYLINE":
                lwp_ent_pts = lwp_ent.points
                if lwp_ent.is_closed:
                    lwp_ent_pts.append(lwp_ent_pts[0])
            if lwp_ent.dxftype == "LINE":
                lwp_ent_pts.append(lwp_ent.start)
                lwp_ent_pts.append(lwp_ent.end)
            for idpt, lwp_pt in enumerate(lwp_ent_pts):
                if idpt < (len(lwp_ent_pts) - 1):
                    start_pt_cc = QgsPointXY(float(lwp_pt[0]), float(lwp_pt[1]))
                    end_pt_cc = QgsPointXY(float(lwp_ent_pts[idpt + 1][0]), float(lwp_ent_pts[idpt + 1][1]))
                    # Creation only if no double point
                    if check_no_dblpt(start_pt_cc, end_pt_cc):
                        # Check if the point is an eliminated point
                        # If yes, use the corresponding RFU point instead
                        for elim_pt in elim_pts:
                            if start_pt_cc == elim_pt[0]:
                                start_pt_cc = elim_pt[1]
                            if end_pt_cc == elim_pt[0]:
                                end_pt_cc = elim_pt[1]
                        start_pt = coords_tr_wgs.transform(start_pt_cc)
                        end_pt = coords_tr_wgs.transform(end_pt_cc)
                        # Creation of the new RFU objects in the layers
                        # Create line geometry
                        line = QgsGeometry.fromPolylineXY([start_pt, end_pt])
                        # Check if the lines intersects
                        to_create = check_limit_cross(line, self.original_l_edge, self.canvas, True)
                        # Creation of the RFU objects in the layer
                        if to_create:
                            # Create the feature
                            edge = QgsFeature()
                            edge.setGeometry(line)
                            edge.setFields(self.l_edge.fields())
                            edge.setAttributes(
                                    [NULL, NULL, self.user])
                            # Add feature to the layer
                            self.l_edge.addFeature(edge)
        # Refresh the canvas
        self.canvas.refresh()

# Manage the window of parameters
class ParamDxf2Rfu(QWidget, gui_dlg_dxf2rfu):

    send_nw_params = pyqtSignal(dict)
    
    def __init__(self, dwg_lyrs, dwg_blocks, nature, precision_class, parent=None):

        super(ParamDxf2Rfu, self).__init__(parent)
        self.setupUi(self)
        # Initialization of the closing method (False= quit by red cross)
        self.quitValid = False
        self.paramDxf = {}
        self.buttValid.clicked.connect(self.buttOk)
        # Delete Widget on close event..
        self.setAttribute(Qt.WA_DeleteOnClose)
        # Load the original parameters
        try:
            self.paramsPath = os.path.join(os.path.dirname(__file__), r"import_dxf2rfu_param.json")
        except IOError as error:
            raise error
        with codecs.open(self.paramsPath, encoding='utf-8', mode='r') as jsonFile:
            self.jsonParams = json.load(jsonFile)
            self.oldParams = self.jsonParams[r"dxfparams"]
        # Create sorted list of the names of dwg layers
        self.dwg_lyrs = dwg_lyrs
        lyrNames = []
        for lyr in self.dwg_lyrs:
            lyrNames.append(str(lyr.name))
        lyrNames.sort()
        # Create sorted list of the names of blocks
        self.dwg_blocks = dwg_blocks
        blkNames = []
        for blkDef in self.dwg_blocks:
            if len(blkDef.name) > 0:
                if (not blkDef.is_xref) and (not blkDef.is_anonymous) and blkDef.name[0] != '*':
                    blkNames.append(str(blkDef.name))
        blkNames.sort()
        self.nature = nature
        self.precision_class = precision_class
        # Populate the precision class list
        precClassDft = None
        precClassCurIdx = 0
        precClassDftExist = False
        if "precClass" in self.oldParams:
            precClassDft = self.oldParams["precClass"]
            for (idx, prec_val) in enumerate(self.precision_class):
                if precClassDft == self.precision_class[idx][1]:
                    precClassCurIdx = idx
                    precClassDftExist = True
            if not precClassDftExist:
                self.precisionClassCmb.addItem(precClassDft)
                self.precisionClassCmb.setItemData(0, QColor("red"), Qt.TextColorRole)
        for precClass in self.precision_class:
            self.precisionClassCmb.addItem(precClass[1])
        self.precisionClassCmb.setCurrentIndex(precClassCurIdx)
        # Populate the layer list (for vertices and edges)
        vtxLyrDft = None
        vtxCurIdx = 0
        if "vtxLyr" in self.oldParams:
            vtxLyrDft = self.oldParams["vtxLyr"]
            if vtxLyrDft in lyrNames:
                vtxCurIdx = lyrNames.index(vtxLyrDft)
            else:
                self.vtxLyrCmb.addItem(vtxLyrDft)
                self.vtxLyrCmb.setItemData(0, QColor("red"), Qt.TextColorRole)
        edgesLyrDft = None
        edgesCurIdx = 0
        if "edgesLyr" in self.oldParams:
            edgesLyrDft = self.oldParams["edgesLyr"]
            if edgesLyrDft in lyrNames:
                edgesCurIdx = lyrNames.index(edgesLyrDft)
            else:
                self.edgesLyrCmb.addItem(edgesLyrDft)
                self.edgesLyrCmb.setItemData(0, QColor("red"), Qt.TextColorRole)
        for lyrName in lyrNames:
            self.vtxLyrCmb.addItem(lyrName)
            self.edgesLyrCmb.addItem(lyrName)
        self.vtxLyrCmb.setCurrentIndex(vtxCurIdx)
        self.edgesLyrCmb.setCurrentIndex(edgesCurIdx)
        # Find the personnalized nature (if exists)
        spec_nat = ""
        for k in list(self.oldParams.keys()):
            if str(k) != "precClass" \
                    and str(k) != "vtxLyr" \
                    and str(k) != "edgesLyr" \
                    and str(k) not in self.nature:
                spec_nat = str(k)
        # Populate the different types of points
        idN = 1
        for idN, ptType in enumerate (self.nature):
            self.symbCorresLab = QLabel(self.ptTypeGpb)
            sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.symbCorresLab.sizePolicy().hasHeightForWidth())
            self.symbCorresLab.setSizePolicy(sizePolicy)
            self.symbCorresLab.setMinimumSize(QSize(160, 0))
            self.symbCorresLab.setMaximumSize(QSize(160, 16777215))
            self.symbCorresLab.setObjectName("symbCorresLab" + str(idN))
            self.symbCorresLab.setText(str(ptType))
            self.gridLayout_2.addWidget(self.symbCorresLab, (idN), 0, 1, 1)
            self.symbCorresCmb = QComboBox(self.ptTypeGpb)
            self.symbCorresCmb.setObjectName("symbCorresCmb" + str(idN))
            self.gridLayout_2.addWidget(self.symbCorresCmb, (idN), 1, 1, 1)
            self.curCmb = self.findChild(QComboBox, "symbCorresCmb" + str(idN))
            self.curCmb.addItem(no_blk)
            self.curCmb.addItem(all_blks)
            blkDft = None
            blkCurIdx = 0
            if str(ptType) in self.oldParams:
                blkDft = self.oldParams[str(ptType)]
                if blkDft in blkNames :
                    blkCurIdx = blkNames.index(blkDft) + 2
                else:
                    if blkDft == no_blk:
                        blkCurIdx = 0
                    elif blkDft == all_blks:
                        blkCurIdx = 1
                    else:
                        self.curCmb.addItem(blkDft)
                        blkCurIdx = 2
                        self.curCmb.setItemData(2, QColor("red"), Qt.TextColorRole)
            for blkName in blkNames:
                self.curCmb.addItem(blkName)
            self.curCmb.setCurrentIndex(blkCurIdx)
        # Add line for using a specific new nature
        idN += 1
        self.symbNwCorresLe = QLineEdit(self.ptTypeGpb)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.symbNwCorresLe.sizePolicy().hasHeightForWidth())
        self.symbNwCorresLe.setSizePolicy(sizePolicy)
        self.symbNwCorresLe.setMinimumSize(QSize(160, 0))
        self.symbNwCorresLe.setMaximumSize(QSize(160, 16777215))
        self.symbNwCorresLe.setObjectName("symbNwCorresLe")
        self.symbNwCorresLe.setPlaceholderText(le_phtxt)
        self.gridLayout_2.addWidget(self.symbNwCorresLe, (idN), 0, 1, 1)
        self.symbCorresCmb = QComboBox(self.ptTypeGpb)
        self.symbCorresCmb.setObjectName("symbCorresCmb" + str(idN))
        self.gridLayout_2.addWidget(self.symbCorresCmb, (idN), 1, 1, 1)
        self.curCmb = self.findChild(QComboBox, "symbCorresCmb" + str(idN))
        self.curCmb.addItem(no_blk)
        self.curCmb.addItem(all_blks)
        blkDft = None
        blkCurIdx = 0
        if spec_nat != "":
            self.symbNwCorresLe.setText(spec_nat)
            blkDft = self.oldParams[str(spec_nat)]
            if blkDft in blkNames :
                blkCurIdx = blkNames.index(blkDft) + 2
            else:
                if blkDft == no_blk:
                    blkCurIdx = 0
                elif blkDft == all_blks:
                    blkCurIdx = 1
                else:
                    self.curCmb.addItem(blkDft)
                    blkCurIdx = 2
                    self.curCmb.setItemData(2, QColor("red"), Qt.TextColorRole)
        for blkName in blkNames:
            self.curCmb.addItem(blkName)
        self.curCmb.setCurrentIndex(blkCurIdx)
        
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem, (idN + 1), 0, 1, 1)
        
    # Close the window when clicking on the OK button
    def buttOk(self):
        self.quitValid = True
        self.close()
        
    # Send the parameters when the windows is quit
    def closeEvent(self, event):
        if self.quitValid:
            # Save the different parameters
            self.paramDxf["vtxLyr"] = self.vtxLyrCmb.currentText()
            self.paramDxf["edgesLyr"] = self.edgesLyrCmb.currentText()
            self.paramDxf["precClass"] = self.precisionClassCmb.currentText()
            for idN, pt_type in enumerate(self.nature):
                typeCmb = self.findChild(QComboBox, "symbCorresCmb" + str(idN))
                self.paramDxf[str(pt_type)] = str(typeCmb.currentText())
            # Add the specific nature
            if self.symbNwCorresLe.text() != "":
                typeCmb = self.findChild(QComboBox, "symbCorresCmb" + str(idN+1))
                self.paramDxf[str(self.symbNwCorresLe.text())] = str(typeCmb.currentText())
            self.hide()
            # Update the new parameters in the json file
            jsonParams = {}
            jsonParams["dxfparams"] = self.paramDxf
            with codecs.open(self.paramsPath, encoding='utf-8', mode='w') as jsonFile:
                jsonFile.write(json.dumps(jsonParams, indent=4, separators=(',', ': '), ensure_ascii=False))
            # Send the parameters
            self.send_nw_params.emit(self.paramDxf)
        else:
            # Hide the window
            self.hide()