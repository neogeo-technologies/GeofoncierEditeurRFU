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
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal, QSize
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QMessageBox, QFileDialog, QLabel, QComboBox, QLineEdit,
                                    QSizePolicy, QSpacerItem, QWidget, QDialog)
from qgis.core import QgsPointXY, QgsWkbTypes, QgsFeature, QgsGeometry, NULL

from functools import partial

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
                 typo_nature_som=[],
                 typo_nature_lim=[],
                 tol_spt=0.0):
        
        self.iface = iface
        self.canvas = canvas
        self.project = project
        self.l_edge = l_edge
        self.l_vertex = l_vertex
        self.user = user
        self.auth_creator = auth_creator
        self.precision_class = precision_class
        self.typo_nature_som = typo_nature_som
        self.typo_nature_lim = typo_nature_lim
        self.tol_spt = tol_spt
        self.cc = selected_ellips_acronym
        self.edge = None
        
    # Import DXF file
    def import_file(self):
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
            self.nw_param_dxf2rfu = ParamDxf2Rfu(self.dwg_lyrs, self.dwg_blocks, self.typo_nature_som, self.typo_nature_lim, self.precision_class, self.auth_creator, self.user)
            # Capture the dic of parameters when closing the dlg window
            self.nw_param_dxf2rfu.send_nw_params.connect(self.dxf_ok_param) 
            # Modal window
            self.nw_param_dxf2rfu.setWindowModality(Qt.ApplicationModal)
            # Show the parameters window
            self.nw_param_dxf2rfu.show()
    
    def dxf_ok_param1(self, dic_param):   
        return None
    
    # Launch the process of creation once the param window is validated
    def dxf_ok_param(self, dic_param):
        self.nw_params = dic_param
        idx_prec = 1
        # Find the creator
        if "createur" in self.nw_params:
            ge_createur = self.nw_params["createur"]
        else:
            ge_createur = self.user
        # Determine the precision class attribute
        for (idx, prec_val) in enumerate(self.precision_class):
            if self.precision_class[idx][1] == self.nw_params["prec_class"]:
                idx_prec = idx
        idx_prec = int(self.precision_class[idx_prec][0])
        # Find delim_pub
        if "delim_pub" in self.nw_params:
            delim_pub = self.nw_params["delim_pub"]
            
        # Create the list of all blk_typo_natures
        blk_lst = []
        if "blk_corrs" in self.nw_params:
            for k in list(self.nw_params["blk_corrs"].keys()):
                blk_lst.append(k)
                
        # Create the list of all lim_typo_natures
        lim_lst = []
        if "lim_lyrs" in self.nw_params:
            for k in list(self.nw_params["lim_lyrs"].keys()):
                lim_lst.append(k)
        
        # Transformations to obtain the WGS84 or the CC coordinates
        coords_tr_wgs, coords_tr_cc = crs_trans_params(self.canvas, self.project)
        
        # Creation of the vertices        
        self.iface.setActiveLayer(self.l_edge)
        self.iface.setActiveLayer(self.l_vertex)    
        elim_pts = []
        vtx_blk_ents = [entity for entity in self.dwg_ents if entity.layer == self.nw_params["vtx_lyr"] and entity.dxftype == "INSERT"]
        for pt_type in blk_lst:
            if self.nw_params["blk_corrs"][pt_type] == all_blks:
                vtx_curtypeblks = vtx_blk_ents
            else:
                vtx_curtypeblks = [entity for entity in vtx_blk_ents if entity.name == self.nw_params["blk_corrs"][pt_type]]
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
                    create_nw_feat( self.l_vertex, 
                                    QgsGeometry.fromPointXY(nw_pt_wgs), 
                                    [NULL, NULL, ge_createur, delim_pub, pt_type, pt_type, idx_prec, float("{0:.02f}".format(nw_pt.x())), float("{0:.02f}".format(nw_pt.y())), self.cc, 0.0, "false", id_ptintol]
                                    )
        
        # Creation of the limits
        self.iface.setActiveLayer(self.l_vertex)
        self.iface.setActiveLayer(self.l_edge)
        for lim_type in lim_lst:            
            edge_ents = [entity for entity in self.dwg_ents if entity.layer == self.nw_params["lim_lyrs"][lim_type] and \
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
                            to_create = check_limit_cross(line, self.original_l_edge, ge_createur, delim_pub, lim_type, self.canvas, True)
                            # Creation of the RFU objects in the layer
                            if to_create:
                                # Create the feature
                                create_nw_feat(self.l_edge, line, [NULL, NULL, ge_createur, delim_pub, lim_type])
        # Refresh the canvas
        self.canvas.refresh()

# Manage the window of parameters
class ParamDxf2Rfu(QWidget, gui_dlg_dxf2rfu):

    send_nw_params = pyqtSignal(dict)
    
    def __init__(self, dwg_lyrs, dwg_blocks, typo_nature_som, typo_nature_lim, precision_class, auth_creator, user, parent=None):

        super(ParamDxf2Rfu, self).__init__(parent)
        self.setupUi(self)
        # Initialization of the closing method (False= quit by red cross)
        self.quit_valid = False
        self.param_dxf = {}
        self.valid_btn.clicked.connect(self.butt_ok)
        # Delete Widget on close event..
        # self.setAttribute(Qt.WA_DeleteOnClose, True)
        # Load the original parameters
        try:
            self.params_path = os.path.join(os.path.dirname(__file__), r"import_dxf2rfu_param.json")
        except IOError as error:
            raise error
        with codecs.open(self.params_path, encoding='utf-8', mode='r') as json_file:
            self.json_params = json.load(json_file)
            self.old_params = self.json_params[r"dxfparams"]
        # Manage delim_pub_chk text
        self.delim_pub_chk.stateChanged.connect(self.settext_delim_pub_chk)
        # Create sorted list of the names of dwg layers
        self.dwg_lyrs = dwg_lyrs
        lyr_names = []
        for lyr in self.dwg_lyrs:
            lyr_names.append(str(lyr.name))
        lyr_names.sort()
        # Create sorted list of the names of blocks
        self.dwg_blocks = dwg_blocks
        blk_names = []
        for blk_def in self.dwg_blocks:
            if len(blk_def.name) > 0:
                if (not blk_def.is_xref) and (not blk_def.is_anonymous) and blk_def.name[0] != '*':
                    blk_names.append(str(blk_def.name))
        blk_names.sort()
        self.typo_nature_som = typo_nature_som
        self.typo_nature_lim = typo_nature_lim
        self.precision_class = precision_class
        self.auth_creator = auth_creator
        self.user = user
        # Fill the delim_pub checkbox
        if "delim_pub" in self.old_params:
            if self.old_params["delim_pub"] == 'true':
                self.delim_pub_chk.setChecked(True)
            else:
                self.delim_pub_chk.setChecked(False)
        # Populate createur list
        creat_param = False
        for i, e in enumerate(self.auth_creator):
            self.createur_cmb.addItem("%s (%s)" % (e[1], e[0]))
            # Find the creator in the params
            if "createur" in self.old_params:
                if self.old_params["createur"] == e[0]:
                    self.createur_cmb.setCurrentIndex(i)
                    creat_param = True 
            # Set current user as the creator by default
            if self.user == e[0] and not creat_param:
                self.createur_cmb.setCurrentIndex(i)
        # Populate the precision class list
        prec_class_dft = None
        prec_class_curidx = 0
        prec_class_dft_exist = False
        if "prec_class" in self.old_params:
            prec_class_dft = self.old_params["prec_class"]
            for (idx, prec_val) in enumerate(self.precision_class):
                if prec_class_dft == self.precision_class[idx][1]:
                    prec_class_curidx = idx
                    prec_class_dft_exist = True
            if not prec_class_dft_exist:
                self.precision_class_cmb.addItem(prec_class_dft)
                self.precision_class_cmb.setItemData(0, QColor("red"), Qt.TextColorRole)
        for prec_class in self.precision_class:
            self.precision_class_cmb.addItem(prec_class[1])
        self.precision_class_cmb.setCurrentIndex(prec_class_curidx)
        # Populate the layer list (for vertices)
        vtx_lyr_dft = None
        vtx_curidx = 0
        if "vtx_lyr" in self.old_params:
            vtx_lyr_dft = self.old_params["vtx_lyr"]
        else:
            vtx_lyr_dft = "0"
        if vtx_lyr_dft in lyr_names:
            vtx_curidx = lyr_names.index(vtx_lyr_dft)
        else:
            self.vtx_lyr_cmb.addItem(vtx_lyr_dft)
            self.vtx_lyr_cmb.setItemData(0, QColor("red"), Qt.TextColorRole)
 

        for lyr_name in lyr_names:
            self.vtx_lyr_cmb.addItem(lyr_name)

        self.vtx_lyr_cmb.setCurrentIndex(vtx_curidx)

        # Populate the different types of points
        for idx, pt_type in enumerate (self.typo_nature_som):
            self.symb_corr_lab = QLabel(self.pt_type_gpb)
            sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.symb_corr_lab.sizePolicy().hasHeightForWidth())
            self.symb_corr_lab.setSizePolicy(sizePolicy)
            self.symb_corr_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.symb_corr_lab.setMinimumSize(QSize(160, 25))
            self.symb_corr_lab.setMaximumSize(QSize(160, 25))
            self.symb_corr_lab.setObjectName("symb_corr_lab" + str(idx))
            self.symb_corr_lab.setText(str(pt_type))
            self.corr_grid_lay.addWidget(self.symb_corr_lab, (idx), 0, 1, 1)
            self.symb_corr_cmb = QComboBox(self.pt_type_gpb)
            self.symb_corr_cmb.setMinimumSize(QSize(0, 25))
            self.symb_corr_cmb.setMaximumSize(QSize(16777215, 25))
            self.symb_corr_cmb.setObjectName("symb_corr_cmb" + str(idx))
            self.corr_grid_lay.addWidget(self.symb_corr_cmb, (idx), 1, 1, 1)
            self.cur_cmb = self.findChild(QComboBox, "symb_corr_cmb" + str(idx))
            # Manage the background color of the comboboxes
            self.cur_cmb.currentTextChanged.connect(partial(self.chk_cmb_bkgrd, self.cur_cmb))
            # Add specific values (all block and no none block)
            self.cur_cmb.addItem(no_blk)
            self.cur_cmb.setItemData(0, QColor(111,111,111), Qt.TextColorRole)
            self.cur_cmb.addItem(all_blks)
            self.cur_cmb.setItemData(1, QColor(42,195,124), Qt.TextColorRole)
            blk_dft = None
            blk_curidx = 0
            # Manage v2.1 new config.json structure
            if "blk_corrs" in self.old_params:
                blks_params = self.old_params["blk_corrs"]
            # Manage old config.json structure
            else:
                blks_params = self.old_params
            # Find the correct param
            if str(pt_type) in blks_params:
                blk_dft = blks_params[str(pt_type)]
            if blk_dft in blk_names :
                blk_curidx = blk_names.index(blk_dft) + 2
            else:
                if blk_dft == no_blk:
                    blk_curidx = 0
                elif blk_dft == all_blks:
                    blk_curidx = 1
                else:
                    self.cur_cmb.addItem(blk_dft)
                    blk_curidx = 2
                    self.cur_cmb.setItemData(2, QColor("red"), Qt.TextColorRole)
            for blk_name in blk_names:
                self.cur_cmb.addItem(blk_name)
            self.cur_cmb.setCurrentIndex(blk_curidx)
                
        sp_item1 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.corr_grid_lay.addItem(sp_item1, (idx + 1), 0, 1, 1)
        # Adapt the size of the dlg
        self.pt_type_gpb.setMinimumSize(QSize(470, 56+29*(idx+1)))
        
        # Populate the different types of limits
        for idx, lim_type in enumerate (self.typo_nature_lim):
            self.lim_corr_lab = QLabel(self.lim_type_gpb)
            sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.lim_corr_lab.sizePolicy().hasHeightForWidth())
            self.lim_corr_lab.setSizePolicy(sizePolicy)
            self.lim_corr_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.lim_corr_lab.setMinimumSize(QSize(160, 25))
            self.lim_corr_lab.setMaximumSize(QSize(160, 25))
            self.lim_corr_lab.setObjectName("lim_corr_lab" + str(idx))
            self.lim_corr_lab.setText(str(lim_type))
            self.lim_grid_lay.addWidget(self.lim_corr_lab, (idx), 0, 1, 1)
            self.lim_corr_cmb = QComboBox(self.lim_type_gpb)
            self.lim_corr_cmb.setMinimumSize(QSize(0, 25))
            self.lim_corr_cmb.setMaximumSize(QSize(16777215, 25))
            self.lim_corr_cmb.setObjectName("lim_corr_cmb" + str(idx))
            self.lim_grid_lay.addWidget(self.lim_corr_cmb, (idx), 1, 1, 1)
            self.cur_cmb = self.findChild(QComboBox, "lim_corr_cmb" + str(idx))
            # Manage the background color of the comboboxes
            self.cur_cmb.currentTextChanged.connect(partial(self.chk_cmb_bkgrd, self.cur_cmb))
            # Add specific value (none layer)
            self.cur_cmb.addItem(no_lyr)
            self.cur_cmb.setItemData(0, QColor(111,111,111), Qt.TextColorRole)
            lyr_dft = None
            lyr_cur_idx = 0
            # Manage v2.1 new config.json structure
            if "lim_lyrs" in self.old_params:
                lim_lyrs_params = self.old_params["lim_lyrs"]
            # Manage old config.json structure
            else:
                lim_lyrs_params = self.old_params  
            # Find the correct param
            if str(lim_type) in lim_lyrs_params:
                lyr_dft = lim_lyrs_params[str(lim_type)]
            else:
                lyr_dft = "0"
            if lyr_dft in lyr_names:
                lyr_cur_idx = lyr_names.index(lyr_dft) + 1
            else:
                if lyr_dft == no_lyr:
                    lyr_cur_idx = 0
                else:
                    self.cur_cmb.addItem(lyr_dft)
                    lyr_cur_idx = 1
                    self.cur_cmb.setItemData(1, QColor("red"), Qt.TextColorRole)
            for lyr_name in lyr_names:
                self.cur_cmb.addItem(lyr_name)
            self.cur_cmb.setCurrentIndex(lyr_cur_idx)
                       
        sp_item2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.lim_grid_lay.addItem(sp_item2, (idx + 1), 0, 1, 1)
        # Adapt the size of the dlg
        self.lim_type_gpb.setMinimumSize(QSize(470, 56+29*(idx+1)))
        
    # Change the text of the delim_pub checkbox
    def settext_delim_pub_chk(self):
        if self.delim_pub_chk.isChecked():
            self.delim_pub_chk.setText('oui')
        else:
            self.delim_pub_chk.setText('non')
        
    # Manage the background color of comboboxes
    # (depends on the color of the current item)
    # And the all block sate -> only one block combobox with this state
    def chk_cmb_bkgrd(self, combo):

        sel_col = "QComboBox QAbstractItemView {selection-background-color: lightgray;}"
        std_bkg_col = "QComboBox:on {background-color: rgb(240, 240, 240);}"
        if combo.itemData(combo.currentIndex(), Qt.TextColorRole) == QColor("red"):
            css = "QComboBox {background-color: rgb(255, 189, 189);}" + sel_col + std_bkg_col
            combo.setStyleSheet(css)
        elif combo.itemData(combo.currentIndex(), Qt.TextColorRole) ==  QColor(42,195,124):
            css = "QComboBox {background-color: rgb(208, 255, 222);}" + sel_col + std_bkg_col
            combo.setStyleSheet(css) 
            for idx, pt_type in enumerate(self.typo_nature_som):
                type_cmb = self.findChild(QComboBox, "symb_corr_cmb" + str(idx))
                if type_cmb:
                    if type_cmb != combo:
                        type_cmb.setCurrentText(no_blk)             
        elif combo.itemData(combo.currentIndex(), Qt.TextColorRole) ==  QColor(111,111,111):
            css = "QComboBox {background-color: rgb(144, 144, 144);}" + sel_col + std_bkg_col
            combo.setStyleSheet(css) 
        else:
            css = ""
            combo.setStyleSheet(css)
            # Deactivate the all_blks combobox if another combox is used
            change = False
            for idx, pt_type in enumerate(self.typo_nature_som):
                type_cmb = self.findChild(QComboBox, "symb_corr_cmb" + str(idx))
                if type_cmb:
                    if type_cmb.currentText() != all_blks and type_cmb.currentText() != no_blk:
                        change = True
            if change:
                for idx, pt_type in enumerate(self.typo_nature_som):
                    type_cmb = self.findChild(QComboBox, "symb_corr_cmb" + str(idx))
                    if type_cmb:
                        if type_cmb.currentText() == all_blks:
                            type_cmb.setCurrentText(no_blk)
    
    # Close the window when clicking on the OK button
    def butt_ok(self):
        self.quit_valid = True
        self.close()
        
    # Send the parameters when the windows is quit
    def closeEvent(self, event):
        if self.quit_valid:
            # Save the different parameters
            self.param_dxf["createur"] = self.createur_cmb.currentText()[-6:-1]
            self.param_dxf["vtx_lyr"] = self.vtx_lyr_cmb.currentText()
            self.param_dxf["prec_class"] = self.precision_class_cmb.currentText()
            # Transform the delim_pub checkbox into the correct value
            self.param_dxf["delim_pub"] = chkbox_to_truefalse(self.delim_pub_chk)
            blk_def = {}
            for idx, pt_type in enumerate(self.typo_nature_som):
                type_cmb = self.findChild(QComboBox, "symb_corr_cmb" + str(idx))
                blk_def[str(pt_type)] = str(type_cmb.currentText())
            self.param_dxf["blk_corrs"] = blk_def
            lim_def = {}
            for idx, lim_type in enumerate(self.typo_nature_lim):
                type_cmb = self.findChild(QComboBox, "lim_corr_cmb" + str(idx))
                lim_def[str(lim_type)] = str(type_cmb.currentText())
            self.param_dxf["lim_lyrs"] = lim_def
            self.hide()
            # Update the new parameters in the json file
            json_params = {}
            json_params["dxfparams"] = self.param_dxf
            with codecs.open(self.params_path, encoding='utf-8', mode='w') as json_file:
                json_file.write(json.dumps(json_params, indent=4, separators=(',', ': '), ensure_ascii=False))
            # Send the parameters
            self.send_nw_params.emit(self.param_dxf)
        else:
            # Hide the window
            self.hide()