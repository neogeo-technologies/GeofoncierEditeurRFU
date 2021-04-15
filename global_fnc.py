# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Global fnc
    * Description:   Global functions
    * First release: 2018-06-01
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                        QgsVectorLayer, QgsProject, QgsSymbol,
                        QgsSingleSymbolRenderer, QgsRuleBasedRenderer, QgsLineSymbol,
                        QgsField, Qgis, QgsFeature, QgsPointXY, QgsMessageLog, QgsWkbTypes,
                        QgsEditorWidgetSetup)
from qgis.PyQt.QtWidgets import QMessageBox, QGridLayout

import math
import os
import json
import codecs

from .global_vars import * 


# Find distance between 2 QgsPoint
def dist_2_pts(pt1, pt2):
    return math.sqrt( (pt2.x() - pt1.x())**2 + (pt2.y() - pt1.y())**2 )


# Find if 2 points are close (to consider it's the same point)
def find_near(pt1, pt2, tol):
    dist = round(math.sqrt( (pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2 ), 3)
    if dist <= tol :
        return [True, dist]
    else :
        return [False, dist]


# Create 2 transformations to obtain WGS84 or CC coordinates (project CRS)
def crs_trans_params(canvas, project):
    crs_cur = canvas.mapSettings().destinationCrs()
    crs_wgs = QgsCoordinateReferenceSystem(4326)
    coords_trf_wgs = QgsCoordinateTransform(crs_cur, crs_wgs, project)
    coords_trf_cc = QgsCoordinateTransform(crs_wgs, crs_cur, project)
    return coords_trf_wgs, coords_trf_cc
    
    
# Create the layer that will be used to store the eliminated lines
def create_elimlyr(canvas):
    elim_lyr = QgsVectorLayer(r"LineString?crs=epsg:4326&index=yes",
                                elimedge_lname, r"memory")
    p_elimedge = elim_lyr.dataProvider()
    QgsProject.instance().addMapLayer(elim_lyr, True)
    # Case of only one color (elimedge_mono set in global_vars)
    if elimedge_mono:
        rend_symb=QgsSymbol.defaultSymbol(elim_lyr.geometryType())
        rend_symb.setWidth(elimedge_wdt)
        rend_symb.setColor(QColor(elimedge_col))
        rend_symb.setOpacity(elimedge_opc)
        rend_elimedge = QgsSingleSymbolRenderer(rend_symb)
    # Case of multiple colors depending on the type of elimination
    else:
        rend_elimedge = QgsRuleBasedRenderer(QgsLineSymbol())
        edge_root_rule = rend_elimedge.rootRule()
        edge_rules = ((inter_rfu, "\"pb_type\" = '" + inter_rfu + "'", elimedge_col, elimedge_wdt),
                      (inter_new, "\"pb_type\" = '" + inter_new + "'", elimedge_col2, elimedge_wdt))
        for label, expression, color, width in edge_rules:
            rule = edge_root_rule.children()[0].clone()
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().setColor(QColor(color))
            rule.symbol().setWidth(width)
            rule.symbol().setOpacity(elimedge_opc)
            edge_root_rule.appendChild(rule)
        edge_root_rule.removeChildAt(0)
    elim_lyr.setRenderer(rend_elimedge)
    p_elimedge.addAttributes(elimlyr_atts)
    elim_lyr.updateFields()
    # Refresh the canvas
    elim_lyr.triggerRepaint()
    return elim_lyr
    
    
# Define the params of a message box (with title, text, informativetext)
def mbox_with_parent_params(wdg_parent, title, text, informative_text):
    mbox = QMessageBox(wdg_parent)
    mbox.setTextFormat(Qt.RichText)
    mbox.setWindowTitle(title)
    mbox.setText(text)
    mbox.setInformativeText(informative_text)
    mbox.addButton("OK", QMessageBox.AcceptRole)
    mbox.setIcon(QMessageBox.Warning)
    return mbox
    
    
# Define the params of a message box (with title, text, informativetext)
def mbox_w_params(title, text, informative_text):
    mbox = QMessageBox()
    mbox.setTextFormat(Qt.RichText)
    mbox.setWindowTitle(title)
    mbox.setText(text)
    mbox.setInformativeText(informative_text)
    mbox.addButton("OK", QMessageBox.AcceptRole)
    mbox.setIcon(QMessageBox.Warning)
    return mbox


# Check if a limit (line) intersects one of the existing limits 
# (in original_l_edge layer). If yes, put this limit
# in the elimedge_lname layer and return False
# If imported = False: use others messages and doesn't create
# eliminated lines
# Also check if two lines are equals
def check_limit_cross(line, original_l_edge, ge_createur, delim_pub, lim_typo_nat, canvas, imported):
    to_create = True
    first_creation = True
    # Check intersection of lines
    for edge_feat in original_l_edge.getFeatures():
        edge_feat_g = edge_feat.geometry()
        if edge_feat_g.type() == QgsWkbTypes.LineGeometry:
            cross_case = ""
            # Check for equality of 2 lines
            if line.isGeosEqual(edge_feat_g):
                # Determine the texts to use (depending on imported lines or manually created lines)
                if imported:
                    txt_rfu = txt_ln_equ_rfu
                    itxt_rfu = inftxt_ln_equ_rfu
                    txt_nw = txt_ln_equ
                    itxt_nw = inftxt_ln_equ
                else:
                    txt_rfu = txt_nwln_equ_rfu
                    itxt_rfu = inftxt_nwln_equ
                    txt_nw = txt_nwln_equ
                    itxt_nw = inftxt_nwln_equ
                # Case of new line equals a RFU line
                if edge_feat['@id_arc']:
                    m_box = mbox_w_params(tl_ln_equ, txt_rfu, itxt_rfu)
                # Case of 2 imported equal lines
                else:
                    m_box = mbox_w_params(tl_ln_equ, txt_nw, itxt_nw)
                m_box.exec_()
                to_create = False
            # Check if 2 lines intersects
            elif line.crosses(edge_feat_g) and first_creation:
                # Determine the texts to use (depending on imported lines or manually created lines)
                if imported:
                    txt_rfu = txt_ln_ints_rfu
                    itxt_rfu = inftxt_ln_ints_rfu.format(elimedge_lname)
                    txt_nw = txt_ln_ints
                    itxt_nw = inftxt_ln_ints.format(elimedge_lname)
                else:
                    txt_rfu = txt_nwln_ints_rfu
                    itxt_rfu = inftxt_nwln_ints
                    txt_nw = txt_nwln_ints
                    itxt_nw = inftxt_nwln_ints
                # Case of new line intersects a RFU line
                if edge_feat['@id_arc']:
                    cross_case = inter_rfu
                    m_box = mbox_w_params(tl_ln_ints, txt_rfu, itxt_rfu)
                # Case of 2 imported lines intersects
                else:
                    cross_case = inter_new
                    m_box = mbox_w_params(tl_ln_ints, txt_nw, itxt_nw)
                m_box.exec_()
                to_create = False
            # Case of imported lines: create the crossing line in a specific layer
            if imported and cross_case != "" and first_creation:
                # If doesn't exist, create a layer that will contain the eliminated lines
                if not QgsProject.instance().mapLayersByName(elimedge_lname):
                    l_elimedge = create_elimlyr(canvas)
                else:
                    l_elimedge = QgsProject.instance().mapLayersByName(elimedge_lname)[0]
                # Create the eliminated line in the specific layer
                # Start editing mode
                if not l_elimedge.isEditable():
                    l_elimedge.startEditing()
                # Create the feature
                elimedge = QgsFeature()
                elimedge.setGeometry(line)
                elimedge.setFields(l_elimedge.fields())
                elimedge.setAttributes([cross_case, ge_createur, delim_pub, lim_typo_nat])
                # Add feature to the layer
                l_elimedge.addFeature(elimedge)
                first_creation = False
    return to_create


# Check if a vertex feature is out of a bbox feature
def check_vtx_outofbbox(vtx_ft, bbox_ft):
    vtx_ft_g = vtx_ft.geometry()
    bbox_ft_g = bbox_ft.geometry()
    to_export = True
    # Check point out of the bbox   
    if vtx_ft_g.disjoint(bbox_ft_g):
        to_export = False
    return to_export


# Check if a edge fetaure is out of a bbox feature or is crossing a bbox feature  
def check_edge_outofbbox(edge_ft, bbox_ft):
    edge_ft_g = edge_ft.geometry()
    bbox_ft_g = bbox_ft.geometry()
    to_export = True
    # Check edge out of the bbox   
    if edge_ft_g.disjoint(bbox_ft_g):
        to_export = False
    # Check edge crossing the bbox   
    if edge_ft_g.crosses(bbox_ft_g):
        to_export = False
    return to_export


# Create the layer that will contains the vertices out of the bbox when exporting
def create_vtx_outofbbox_lyr():
    vtx_outofbbox_lyr = QgsVectorLayer(r"Point?crs=epsg:4326&index=yes",
                                  vtx_outofbbox_lname, r"memory")
    p_vtx_outofbbox_lyr = vtx_outofbbox_lyr.dataProvider()
    QgsProject.instance().addMapLayer(vtx_outofbbox_lyr, True)
    # Create a simple symbol
    rend_symb=QgsSymbol.defaultSymbol(vtx_outofbbox_lyr.geometryType())
    rend_symb.setSize(vtx_outofbbox_size)
    rend_symb.setColor(QColor(vtx_outofbbox_color))
    rend_symb.setOpacity(vtx_outofbbox_opc)
    rend_vtx_outofbbox = QgsSingleSymbolRenderer(rend_symb)
    vtx_outofbbox_lyr.setRenderer(rend_vtx_outofbbox)
    p_vtx_outofbbox_lyr.addAttributes(vtx_atts)
    vtx_outofbbox_lyr.updateFields()
    # Refresh the canvas
    vtx_outofbbox_lyr.triggerRepaint()
    return vtx_outofbbox_lyr
 
 
# Create the layer that will contains the edges out of the bbox when exporting
def create_edge_outofbbox_lyr():
    edge_outofbbox_lyr = QgsVectorLayer(r"LineString?crs=epsg:4326&index=yes",
                                  edge_outofbbox_lname, r"memory")
    p_edge_outofbbox_lyr = edge_outofbbox_lyr.dataProvider()
    QgsProject.instance().addMapLayer(edge_outofbbox_lyr, True)
    # Create a simple symbol
    rend_symb=QgsSymbol.defaultSymbol(edge_outofbbox_lyr.geometryType())
    rend_symb.setWidth(edge_outofbbox_width)
    rend_symb.setColor(QColor(edge_outofbbox_color))
    rend_symb.setOpacity(edge_outofbbox_opc)
    rend_edge_outofbbox = QgsSingleSymbolRenderer(rend_symb)
    edge_outofbbox_lyr.setRenderer(rend_edge_outofbbox)
    p_edge_outofbbox_lyr.addAttributes(edge_atts)
    edge_outofbbox_lyr.updateFields()
    # Refresh the canvas
    edge_outofbbox_lyr.triggerRepaint()
    return edge_outofbbox_lyr


# Add the list of predefined values to a field
# lyr = layer of the field to be modified
# fld_name = name of the field to modify
# val_list = list of predefined values
#            if the list contains unique values:
#               attribute description = attribute value
#            if the list contains values as a list:
#               attribute value = sublist[idx_val]
#               attribute description = sublist[idx_desc]
def map_predefined_vals_to_fld(lyr, fld_name, val_lst, *idx):    
    if len(idx) == 2:
        idx_val = idx[0]
        idx_desc= idx[1]
    fld_idx = lyr.fields().indexFromName(fld_name)
    fld_values = {}
    for fld_val in val_lst:
        if type(fld_val) == tuple:
            fld_values[fld_val[idx_desc]] = fld_val[idx_val]
        else:
            fld_values[fld_val] = fld_val
    ew_setup = QgsEditorWidgetSetup( 
                    'ValueMap', 
                    {'map': fld_values}
                  )
    try:
        lyr.setEditorWidgetSetup(fld_idx, ew_setup)
        return True
    except:
        return False


# Check if 2 points are equals
def check_no_dblpt(pt1, pt2):
    to_create = True
    if pt1 == pt2:
        to_create = False
    return to_create


# Round a QgsPointXY to cm (2 digits after the point)
def round_pt_2_cm(qgs_pt):
    return QgsPointXY(round(qgs_pt.x(), 2), round(qgs_pt.y(), 2))


# Check if 2 points are identical
# digit = number of digit taken into account for the comparison
def check_identical_pts(qgs_pt1, qgs_pt2, digit):
    ret = False
    if round(qgs_pt1.x(), digit) == round(qgs_pt2.x(), digit) and \
        round(qgs_pt1.y(), digit) == round(qgs_pt2.y(), digit):
        ret = True
    return ret


# Check if 2 lines (2 points lines) are identical
# digit = number of digit taken into account for the comparison
def check_identical_lines(qgs_line1, qgs_line2, digit):
    ret = False
    if (round(qgs_line1[0].x(), digit) == round(qgs_line2[0].x(), digit) and \
        round(qgs_line1[0].y(), digit) == round(qgs_line2[0].y(), digit) and \
        round(qgs_line1[-1].x(), digit) == round(qgs_line2[-1].x(), digit) and \
        round(qgs_line1[-1].y(), digit) == round(qgs_line2[-1].y(), digit)) or \
        (round(qgs_line1[0].x(), digit) == round(qgs_line2[-1].x(), digit) and \
        round(qgs_line1[0].y(), digit) == round(qgs_line2[-1].y(), digit) and \
        round(qgs_line1[-1].x(), digit) == round(qgs_line2[0].x(), digit) and \
        round(qgs_line1[-1].y(), digit) == round(qgs_line2[0].y(), digit)):
        ret = True
    return ret


# Find the max length among several lists
def find_maxlength(self, *val_lists):
    ret_len = 0
    if len(val_lists) > 0:
        for val_list in val_lists:
            if type(val_list) == list:
                if len(val_list) > ret_len:
                    ret_len = len(val_list)
    return ret_len


# Check if a layer (by its name) exists
def layer_exists(layer_name, prj_instance):
    exists = False
    layer_lst = prj_instance.mapLayersByName(layer_name)
    if len(layer_lst) > 0:
        exists = True
    return exists


# Return a list of dictionnaries containing all the attribute values of a specific feature
# The specific feature is given by the value (find_val) of one attribute (in_att)
# respecting the condition cond_fld = cond_val
# If cond_fld == '', no condition (all the values of the field)
# The list contains the different features found respecting those rules
def getmulti_fields_values_from_one_value(lyr, find_val, in_att, cond_val, cond_fld):
    obj_lst = []
    for obj in lyr.getFeatures():
        att_val_dic = {}
        if cond_fld != '':
            if obj[in_att] == find_val and obj[cond_fld] == cond_val:
                atts = get_layer_fields(lyr)
                for att in atts:
                    att_val_dic[att] = obj[att]
                obj_lst.append(att_val_dic)
        else:
            if obj[in_att] == find_val:
                atts = get_layer_fields(lyr)
                for att in atts:
                    att_val_dic[att] = obj[att]
                obj_lst.append(att_val_dic)
    return obj_lst


# Retrun a list of features respecting the condition cond_fld = cond_val
def feats_by_cond(lyr, cond_fld, cond_val):
    ft_lst = []
    for obj in lyr.getFeatures():
        if obj[cond_fld] == cond_val:
            ft_lst.append(obj)
    return ft_lst


# Returns a dictionnary containing all the attribute values of a specific feature
def get_fields_values_from_feat(lyr, feat):
    att_val_dic = {}
    atts = get_layer_fields(lyr)
    for att in atts:
        att_val_dic[att] = feat[att]
    return att_val_dic


# Return sorted list of fields of a layer instance
def get_layer_fields(layer):
    fld_lst = []
    for field in layer.fields():
        fld_lst.append(field.name())
    return sorted(fld_lst, key=locale.strxfrm)


# Transform a checkbox state in True/False string value
def chkbox_to_truefalse(chkbox):
    if chkbox.isChecked():
        return 'True'
    else:
        return 'False'


# Create a new feature in a specific layer
# lyr = layer
# geom = QgsGeometry
# atts_val = list of attributes values
def create_nw_feat(lyr, geom, atts_val):
    nw_feat = QgsFeature()
    nw_feat.setGeometry(geom)
    nw_feat.setFields(lyr.fields())
    nw_feat.setAttributes(atts_val)
    lyr.addFeature(nw_feat)
    return nw_feat


######################################################
# FOR DEBUGGING
######################################################
       
# Show the debug messages
# Usage: 
# debug_msg('DEBUG', "var1: %s, - var2: %s" , (str(var1), str(var2)))
# debug_msg('DEBUG', "var1: %s" , (str(var1)))
def debug_msg(debug_on_off, msg_str, msg_list_var):
    if debug_on_off == 'DEBUG':
        msg = msg_str % msg_list_var
        QgsMessageLog.logMessage(msg, 'Sgm debug')


# Export the urlopen response to a text file
def urlresp_to_file(resp_read):
    with open(r"C:\DummyDir\_QGIS-RFU_fic_resp.txt", 'a') as fic_resp:
        fic_resp.write(resp_read.decode('utf-8'))
        # fic_resp.write(str(resp_read))


# Export the put data to a file
def putdata_to_file(data):
    with open(r"C:\DummyDir\_QGIS-RFU_putdata.txt", 'a') as fic_resp:
        fic_resp.write(data.decode('utf-8'))
        # fic_resp.write(str(resp_read))


# Change pourcent characters
def unpourcent_char(data):
    for old_c, nw_c in pc_cor.items():
        data = data.replace(old_c, nw_c)
        debug_msg('DEBUG', r"new-data: %s" , (data))
    return data
        