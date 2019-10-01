# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Show capabilities
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the possibility to show the 
    *                capabilities C1 and C2
    * First release: 2019-07-24
    * Last release:  2019-08-19
    * Copyright:     (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QAbstractTableModel
from qgis.PyQt.QtWidgets import QDialog

import os
import xml.etree.ElementTree as ElementTree
import operator

from .global_vars import *
from .global_fnc import *
from .resize_dlg import ResizeDlg

gui_dlg_show_capabilities, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_show_capabilities.ui"))


class ShowCapabilities(QDialog, gui_dlg_show_capabilities):

    def __init__(self, resp_cap, resp_mycap, parent=None):

        super(ShowCapabilities, self).__init__(parent)
        self.setupUi(self)

        self.resp_cap = resp_cap
        self.resp_mycap = resp_mycap
        
        self.resize_dlg = ResizeDlg(self, "dlg_show_capabilities")
        self.resize_params = self.resize_dlg.load_dlgresize()
        self.resize_on = self.resize_params["dlg_show_capabilities"]

        self.buttValid.clicked.connect(self.close)  
        self.buttResize.clicked.connect(self.resize_dlg.dlg_ch_resize)
        # DEBUG
        # urlresp_to_file(self.resp_mycap)
        
        # Populates api key capabilities tab
        if self.resp_mycap:
            tree = ElementTree.fromstring(self.resp_mycap)
            elt_cmt = tree.find(r"./cle_api_rfu/commentaire")
            elt_ext = tree.find(r"./cle_api_rfu/extraction_rfu")
            elt_maj = tree.find(r"./cle_api_rfu/mise_a_jour_rfu")
            elt_lng = tree.find(r"./cle_api_rfu/extraction_rfu_limite")
            if elt_cmt is not None:
                self.cmtLed.setText(elt_cmt.text)
            if elt_ext is not None:
                self.extLed.setText(elt_ext.text)
            if elt_maj is not None:
                self.majLed.setText(elt_maj.text)
            if elt_lng is not None:
                self.lngLed.setText(elt_lng.text + " " + elt_lng.attrib[r"unit"])
        
        # Populates user's capabilities tab
        if self.resp_cap:
            tree = ElementTree.fromstring(self.resp_cap)
            err = tree.find(r"./erreur")
            if err:
                raise Exception(err.text)
            cap_vals = []
            # Find the list of values for each capability
            for i in range(6):
                cap_val = []
                cap_vals.append(cap_val)
            self.entry = tree.find(r"./systeme_geodesique")
            cap_vals[0].append(self.join_att_value(r"code"))
            for self.entry in tree.findall(r"./classe_rattachement/classe"):
                cap_vals[1].append(self.join_att_value(r"som_precision_rattachement"))
            for self.entry in tree.findall(r"./representation_plane_sommet_autorise/representation_plane_sommet"):
                cap_vals[2].append(self.join_att_value(r"som_representation_plane"))
            for self.entry in tree.findall(r"./nature_sommet_conseille/nature"):
                cap_vals[3].append(self.entry.text)
            for self.entry in tree.findall(r"./som_ge_createur_autorise/som_ge_createur"):
                cap_vals[4].append(self.join_att_value("num_ge"))            
            self.entry = tree.find(r"./tolerance")
            cap_vals[5].append("%s %s" % (self.entry.text, self.entry.attrib[r"unit"]))
                
            # Find the number of rows
            nb_rows = find_maxlength(cap_vals[0], cap_vals[1], cap_vals[2], cap_vals[3],
                                            cap_vals[4], cap_vals[5])
            # Create the tableview
            captbl_data = []
            captbl_hd = []
            # Build the header
            for att in captbl_table_hd:
                captbl_hd.append(att[1])
            # Build the contents
            for i in range(nb_rows):
                captbl_row = []
                for cap_val in cap_vals:
                    if len(cap_val) > i:
                        captbl_row.append(cap_val[i])
                    else:
                        captbl_row.append("")
                captbl_data.append(captbl_row)
            captbl_model=MyTableModel(self, captbl_data, captbl_hd)
            # Populate data in the tableview
            self.caputilTbv.setModel(captbl_model)
            self.height_tbv = 0
            self.width_tbv = 0
            # Set column width to fit contents
            self.caputilTbv.resizeColumnsToContents()
            # Increase a little bit the width of the columns
            for id_col, val_col in enumerate(captbl_hd):
                nw_size = self.caputilTbv.columnWidth(id_col) + 5
                self.caputilTbv.setColumnWidth(id_col, nw_size)
                self.width_tbv += nw_size
            # Set row height
            self.caputilTbv.resizeRowsToContents()
            self.height_tbv = (self.caputilTbv.rowHeight(0)) * (nb_rows+1)
            self.width_tbv += 50
            self.height_tbv += 100 
            self.resize_dlg.wtbv = self.width_tbv
            self.resize_dlg.htbv = self.height_tbv
            # Hide vertical header
            vh = self.caputilTbv.verticalHeader()
            vh.setVisible(False)
            # Find the tableview size
            if self.resize_on:
                self.resize_dlg.dlg_auto_resize()

    # Create a new string with attrib + text and a separator
    def join_att_value(self, att):
        return "%s - %s" % (self.entry.attrib[att], self.entry.text)
        
            
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
