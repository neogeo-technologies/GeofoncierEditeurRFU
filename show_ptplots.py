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
    * Last release:  2019-09-24
    * Copyright:     (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QAbstractTableModel
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QBrush, QColor

import os
import xml.etree.ElementTree as ElementTree
import operator

from .global_vars import *
from .global_fnc import *
from .resize_dlg import ResizeDlg

gui_dlg_show_ptplots, _ = uic.loadUiType(
        os.path.join(os.path.dirname(__file__), r"gui/dlg_show_ptplots.ui"))


class ShowPtPlots(QDialog, gui_dlg_show_ptplots):

    ptplotsNwPtSelect = pyqtSignal()
    
    def __init__(self, conn, zone, resp_plots, plot_mode, parent=None):

        super(ShowPtPlots, self).__init__(parent)
        self.setupUi(self)

        self.conn = conn
        self.zone = zone
        self.resp_plots = resp_plots
        # The dlg is used in 2 modes:
        # plot_mode = "info": consultation of the plots
        # plot_mode = "del": deletion of a plot
        self.plot_mode = plot_mode
        
        self.resize_dlg = ResizeDlg(self, "dlg_show_ptplots")
        self.resize_params = self.resize_dlg.load_dlgresize()
        self.resize_on = self.resize_params["dlg_show_ptplots"]
        
        self.buttValid.clicked.connect(self.close)
        self.buttResize.clicked.connect(self.resize_dlg.dlg_ch_resize)
        self.buttNwPtSelect.clicked.connect(self.nw_pt_select)
        
        # Delete Widget on close event
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        if self.plot_mode == "del":
            self.buttNwPtSelect.hide()
            
    # Launch the dlg appearence
    def plots_show(self):
        
        # DEBUG
        # urlresp_to_file(self.resp_plots)
        
        tree = ElementTree.fromstring(self.resp_plots)     
        # Populates ptplots tableview
        if self.resp_plots:
            err = tree.find(r"./erreur")
            if err:
                raise Exception(err.text)
            self.entry = tree.find(r"./sommet")
            self.id_node = self.entry.attrib["id_noeud"]
            self.idnodeLab.setText(plot_dif_txt[self.plot_mode][2] % self.id_node)
            ptplot_vals = []
            for i in range(13):
                ptplot_val = []
                ptplot_vals.append(ptplot_val)
            nb_rows = 0
            nb_valid = 0
            # For each plot find all the infos
            for ptplot in tree.findall(r"./sommet/determination"):
                nb_rows +=1
                ptplot_vals[0].append(ptplot.attrib["det_id"])
                ptplot_vals[1].append(ptplot.find("det_ge_createur").text)
                ptplot_vals[2].append(ptplot.find("det_x").text)
                ptplot_vals[3].append(ptplot.find("det_y").text)
                ptplot_vals[4].append(ptplot.find("det_classe").text)
                ptplot_vals[5].append(ptplot.find("det_srs").text)
                ptplot_vals[6].append(ptplot.find("det_date").text)
                ptplot_vals[7].append(ptplot.find("det_distance_node").text)
                ptplot_vals[8].append(ptplot.find("det_tolerance").text)
                qua_txt = ptplot.find("det_attest_qualite").text.replace(rpl_true[0], rpl_true[2]).replace(rpl_false[0], rpl_false[2])
                ptplot_vals[9].append(qua_txt)
                ptplot_vals[10].append(ptplot.find("det_cs").text)
                st_txt = ptplot.find("det_statut_actif").text.replace(rpl_true[0], rpl_true[1]).replace(rpl_false[0], rpl_false[1])
                if st_txt == "Valide":
                    nb_valid += 1
                ptplot_vals[11].append(st_txt)
                ptplot_vals[12].append(ptplot.find("det_statut_date_change").text)
                           
            # Create the tableview
            self.ptplottbl_data = []
            ptplottbl_hd = []
            # Build the header
            for att in ptplottbl_table_hd:
                ptplottbl_hd.append(att[1])
            # Build the contents
            for i in range(nb_rows):
                ptplottbl_row = []
                for ptplot_val in ptplot_vals:
                    if len(ptplot_val) > i:
                        ptplottbl_row.append(ptplot_val[i])
                    else:
                        ptplottbl_row.append("")
                self.ptplottbl_data.append(ptplottbl_row)
            ptplottbl_model=MyTableModel(self, self.ptplottbl_data, ptplottbl_hd)
            # Populate data in the tableview
            self.ptplotsTbv.setModel(ptplottbl_model)
            self.height_tbv = 0
            self.width_tbv = 0
            # Set column width to fit contents
            self.ptplotsTbv.resizeColumnsToContents()
            # Increase a little bit the width of the columns
            for id_col, val_col in enumerate(ptplottbl_hd):
                nw_size = self.ptplotsTbv.columnWidth(id_col) + 5
                self.ptplotsTbv.setColumnWidth(id_col, nw_size)
                self.width_tbv += nw_size
            # Set row height
            self.ptplotsTbv.resizeRowsToContents()
            self.height_tbv = (self.ptplotsTbv.rowHeight(0)) * (nb_rows+1)
            self.width_tbv += 25
            self.height_tbv += 92
            self.resize_dlg.wtbv = self.width_tbv
            self.resize_dlg.htbv = self.height_tbv
            # Hide vertical header
            vh = self.ptplotsTbv.verticalHeader()
            vh.setVisible(False)
            if self.resize_on:
                self.resize_dlg.dlg_auto_resize()
            # Case of deletion
            if self.plot_mode == "del":
                if nb_valid == 1:
                    m_box = mbox_with_parent_params(self, plot_no_del_msg[0], plot_no_del_msg[1], plot_no_del_msg[2])
                    ret = m_box.exec_() 
                    self.close()
                else:
                    self.ptplotsTbv.clicked.connect(self.del_plot)
            self.show()   

    def del_plot(self):
        # Find the selected cell (considering only the first selected cell)
        idx = self.ptplotsTbv.selectedIndexes()[0].row()
        det_id = self.ptplottbl_data[idx][0]
        # Ensure message
        sure_msg = QMessageBox.question(self, tl_plot_delimp_sure, msg_plot_delimp_sure,
                                    QMessageBox.Yes, QMessageBox.No)
        if sure_msg != QMessageBox.Yes:
            return
        # Check if the plot to delete is not already canceled
        if self.ptplottbl_data[idx][11] == rpl_true[1]:
            resp = self.conn.cancel_plot(self.id_node, det_id, self.zone)
            resp_del_plot_put = resp.read()
            
            tree = ElementTree.fromstring(resp_del_plot_put)
            if resp.code != 200:
                # Catch the error specified by the API          
                elt_err = tree.find(r"./log")
                if elt_err.text:
                    msg = elt_err.text
                else:
                    # Error returned by the server (all other cases)
                    msg = str(resp_del_plot_put)
                # Display the error in a message box
                return QMessageBox.warning(self, tl_plot_delimp, msg)
            # Message deletion succeeded
            else:
                QMessageBox.information(self, tl_plot_delok, msg_plot_delok)
                self.close()
        # Case of a plot already canceled
        else:
            QMessageBox.warning(self, tl_plot_delimp, msg_plotcancd_del)
        
    # Create a new string with attrib + text and a separator
    def join_att_value(self, att):
        return "%s - %s" % (self.entry.attrib[att], self.entry.text)
        
    def nw_pt_select(self):
        self.ptplotsNwPtSelect.emit()
        self.close()
    
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
        elif role == Qt.BackgroundRole:
            # Set 2 different background colors, regarding the det_statut_actif param
            if self.data(self.index(index.row(), 11), Qt.DisplayRole) == rpl_false[1]:
                return QBrush(QColor(st_false_bkgcol))
            else:
                return QBrush(QColor(st_true_bkgcol))
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
