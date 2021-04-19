# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Editor RFU Geofoncier
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the RFU editor
    * First release: 2015
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license 
    ***************************************************************************
"""


from qgis.PyQt.QtCore import Qt, QVariant, QObject, pyqtSignal, QCoreApplication
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QWidget, QMenu
from qgis.PyQt.QtGui import QIcon, QCursor
from qgis.core import Qgis, QgsProject, QgsGeometry
from qgis.utils import iface
from qgis.gui import QgsMessageBar, QgsMapToolIdentifyFeature

import os.path
import xml.etree.ElementTree as ElementTree
from functools import partial

from . import resources_rc
from . import tools
from .rfu_connector import RFUDockWidget
from .vertex_creator import VertexCreator
from .edge_creator import EdgeCreator
from .login import GeoFoncierAPILogin
from .global_vars import * 
from .global_fnc import *
from .import_dxf2rfu import ImportDxf2Rfu
from .import_csvrfu import ImportCsvRfu
from .cut_oldlimit import CutOldLimit
from .show_capabilities import ShowCapabilities
from .show_ptplots import ShowPtPlots
from .transfo_pttoplot import TransfoPtToPlot


class EditorRFUGeofoncier:

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface

        self.canvas = self.iface.mapCanvas()
        self.project = QgsProject.instance()

        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        self.conn = None
        self.rfu = None
        self.edge_creator = None
        self.tol_spt = 0.0
        self.dxf2rfu_import = None
        self.csv2rfu_import = None
        self.show_ptplots = None


    def unload(self):

        # Remove the plugin menu and toolbar
        if self.rfu_menu != None:
            self.iface.mainWindow().menuBar().removeAction(self.rfu_menu.menuAction())
            self.rfu_menu.deleteLater()
            self.iface.mainWindow().removeToolBar(self.toolbar)
        else:
            self.iface.removePluginMenu("&RFU", self.rfu_menu.menuAction())
            self.rfu_menu.deleteLater()

        # Remove RFU dockwidgets
        if self.rfu:
            self.iface.removeDockWidget(self.rfu)
        if self.edge_creator:
            self.iface.removeDockWidget(self.edge_creator)
            
        
    def initGui(self):

        # Add specific menu to QGIS menu
        self.rfu_menu = QMenu(QCoreApplication.translate("RFU", mnu_title_txt))
        self.iface.mainWindow().menuBar().insertMenu(self.iface.firstRightStandardMenu().menuAction(), self.rfu_menu)
        
        # Add specific toolbar
        self.toolbar = self.iface.addToolBar(mnu_title_txt)
        self.toolbar.setObjectName("GeofoncierRfuEditorToolBar")

        # Create actions
        self.action_login = QAction(
            QIcon(r":/resources/rfu_btn_log_in"),
            "S'identifer", self.iface.mainWindow())
        self.action_login.setEnabled(True)
        self.action_login.setCheckable(True)

        self.action_connector = QAction(
            QIcon(r":/resources/rfu_btn_conn_rfu"),
            "Connection à l'API Géofoncier", self.iface.mainWindow())
        self.action_connector.setEnabled(False)
        self.action_connector.setCheckable(True)

        self.action_vtx_creator = QAction(
            QIcon(r":/resources/rfu_btn_add_vtx"),
            "Ajouter un sommet RFU", self.iface.mainWindow())

        self.action_edge_creator = QAction(
            QIcon(r":/resources/rfu_btn_add_edge"),
            "Ajouter une limite RFU", self.iface.mainWindow())
        self.action_edge_creator.setCheckable(True)
        
        self.action_import_csv2rfu = QAction(
            QIcon(r":/resources/rfu_btn_import_csvrfu"),
            "Importer un fichier CSV spécifique RFU", self.iface.mainWindow())

        self.action_import_dxf2rfu = QAction(
            QIcon(r":/resources/rfu_btn_import_dxf2rfu"),
            "Importer un fichier DXF filtré pour le RFU", self.iface.mainWindow())
            
        self.action_cut_oldlimit = QAction(
            QIcon(r":/resources/rfu_btn_cut_oldlimit"),
            "Couper une limite existante par un ou plusieurs sommets nouveaux", self.iface.mainWindow())
            
        self.action_transfo_pt_to_plot = QAction(
            QIcon(r":/resources/rfu_btn_pt_to_plot"),
            "Traiter les sommets proches à transformer en détermination", self.iface.mainWindow())
            
        self.action_del_ptplot = QAction(
            QIcon(r":/resources/rfu_btn_del_ptplot"),
            "Supprimer une détermination d'un sommet", self.iface.mainWindow())
            
        self.action_show_ptplots = QAction(
            QIcon(r":/resources/rfu_btn_show_ptplots"),
            "Consulter les déterminations d'un sommet", self.iface.mainWindow())
            
        self.action_show_capabilities = QAction(
            QIcon(r":/resources/rfu_btn_show_capabilities"),
            "Visualiser les paramètres de l'application", self.iface.mainWindow())
        self.action_show_capabilities.setEnabled(False)
        
        # Deactivate creation and import tools
        self.allow_creation(False)
        
        # Add actions to the toolbar
        self.toolbar.addActions([self.action_login,
                                 self.action_connector,
                                 self.action_vtx_creator,
                                 self.action_edge_creator,
                                 self.action_import_csv2rfu,
                                 self.action_import_dxf2rfu,
                                 self.action_cut_oldlimit,
                                 self.action_transfo_pt_to_plot,
                                 self.action_del_ptplot,
                                 self.action_show_ptplots,
                                 self.action_show_capabilities])
                                 
        # Add actions to the menu
        self.rfu_menu.addActions([self.action_login,
                                 self.action_connector,
                                 self.action_vtx_creator,
                                 self.action_edge_creator,
                                 self.action_import_csv2rfu,
                                 self.action_import_dxf2rfu,
                                 self.action_cut_oldlimit,
                                 self.action_transfo_pt_to_plot,
                                 self.action_del_ptplot,
                                 self.action_show_ptplots,
                                 self.action_show_capabilities])

        # Manage signals..
        self.iface.currentLayerChanged.connect(self.on_toggled)
        self.project.layersRemoved.connect(self.on_layers_removed)

        self.action_login.triggered.connect(self.tool_login_on_triggered)
        self.action_connector.triggered[bool].connect(self.tool_rfu_on_triggered)
        self.action_vtx_creator.triggered.connect(self.tool_vtx_creator_on_triggered)
        self.action_edge_creator.triggered[bool].connect(self.tool_edge_creator_on_triggered)
        self.action_import_csv2rfu.triggered.connect(self.tool_import_csvrfu)
        self.action_import_dxf2rfu.triggered.connect(self.tool_import_dxf2rfu)
        self.action_cut_oldlimit.triggered.connect(self.tool_cut_oldlimit)
        self.action_transfo_pt_to_plot.triggered.connect(self.tool_transfo_pt_to_plot)
        self.action_del_ptplot.triggered.connect(partial(self.tool_select_pt_to_plot, "del"))
        self.action_show_ptplots.triggered.connect(partial(self.tool_select_pt_to_plot, "info"))
        self.action_show_capabilities.triggered.connect(self.tool_show_capabilities)
        # Initialize current layer to None (See switch_editing())..
        self.current_layer = None
        
        
    # On iface Signals
    # ================

    def on_toggled(self):

        layer = self.canvas.currentLayer()
        
        if not layer or not self.rfu:
            return

        if layer.isEditable() and layer == self.rfu.l_vertex:
            self.switch_editing(layer)
        elif layer.isEditable() and layer == self.rfu.l_edge:
            self.switch_editing(layer)


    def switch_editing(self, layer):
        
        old_layer = None

        if self.current_layer is not None:
            old_layer = self.current_layer
            old_layer.committedFeaturesAdded.disconnect(self.on_committed_features_added)
            old_layer.committedFeaturesRemoved.disconnect(self.on_committed_features_removed)
            old_layer.attributeValueChanged.disconnect(self.on_attribute_value_changed)
            old_layer.geometryChanged.disconnect(self.on_geometry_changed)

        self.current_layer = layer
        layer.committedFeaturesAdded.connect(self.on_committed_features_added)
        layer.committedFeaturesRemoved.connect(self.on_committed_features_removed)
        layer.attributeValueChanged.connect(self.on_attribute_value_changed)
        layer.geometryChanged.connect(self.on_geometry_changed)  


    def on_committed_features_added(self, layer_id, features):
        self.rfu.add_features(layer_id, features)


    def on_committed_features_removed(self, layer_id, ft_id_list):
        self.rfu.remove_features(layer_id, ft_id_list)


    def on_geometry_changed(self, fid, geom):
        feature = tools.get_feature_by_id(self.current_layer, fid)
        self.rfu.modify_feature(self.current_layer.id(), feature)


    def on_attribute_value_changed(self, fid, field_idx, value):
        feature = tools.get_feature_by_id(self.current_layer, fid)
        self.rfu.modify_feature(self.current_layer.id(), feature)


    # On map layer registry signals
    # =============================

    def on_layers_removed(self, layers):
        self.current_layer = None


    # Login/logout
    # ============

    def open_connection(self):

        dlg_login = GeoFoncierAPILogin()
        dlg_login.closed.connect(self.dlg_login_on_closed)
        dlg_login.opened.connect(self.dlg_login_on_opened)
        dlg_login.show()

        if not dlg_login.exec_():
            return None

        self.conn = dlg_login.conn
        self.action_connector.setEnabled(True)
        self.action_show_capabilities.setEnabled(True)

        self.iface.messageBar().pushMessage(
                "Géofoncier", "Bonjour %s %s." % (self.conn.prenom, self.conn.nom),
                Qgis.Info, duration=6)


    def close_connection(self):

        msg = ("Voulez-vous fermer votre session ?\n"
               "Attention, toute modification sera perdue.")
        resp = QMessageBox.question(self.iface.mainWindow(), r"Question", msg,
                                    QMessageBox.Yes, QMessageBox.No)
        if resp != QMessageBox.Yes:
            self.dlg_login_on_closed();
            return False

        # Close connection
        if self.rfu:
            if self.rfu:
                self.rfu.reset()
                try:
                    self.rfu.disconn_scale_limit()
                except:
                    pass
                self.rfu.close()
            self.action_connector.setChecked(False)
            self.action_connector.setEnabled(False)
            self.action_show_capabilities.setEnabled(False)
            self.allow_creation(False)

        self.conn = None

        self.iface.messageBar().pushMessage("Géofoncier", "À bientôt.", Qgis.Info, duration=6)


    # On action signals
    # =================

    def dlg_login_on_closed(self):

        if self.conn == None:
            self.action_login.setChecked(False)
        else:
            self.action_login.setChecked(True)
            

    def dlg_login_on_opened(self):

        self.action_login.setChecked(True)


    def tool_login_on_triggered(self, checked):

        if checked:
            self.open_connection()
        else:
            self.close_connection()
            

    def tool_rfu_on_triggered(self, checked):

        if checked and not self.rfu:
            self.rfu = RFUDockWidget(self.iface, self.canvas, self.project, conn=self.conn)
            self.rfu.setObjectName(r"RFUDockWidget")
            self.iface.addDockWidget(Qt.TopDockWidgetArea, self.rfu)
            self.rfu.closed.connect(self.rfu_on_closed)
            self.rfu.uploaded.connect(self.rfu_on_uploaded)
            self.rfu.downloaded.connect(self.rfu_on_downloaded)
            self.rfu.rfureset.connect(self.rfu_on_reset)

        if checked and self.rfu:
            self.rfu.show()

        if not checked:
            self.rfu.hide()


    def rfu_on_closed(self):

        self.action_connector.setChecked(False)


    def rfu_on_uploaded(self):

        if self.edge_creator:
            self.on_edge_creator_destroyed()
            
        # Change the current layer
        self.iface.setActiveLayer(self.rfu.l_edge)
        self.iface.setActiveLayer(self.rfu.l_vertex)
            
            
    def rfu_on_downloaded(self):

        # Allow creation and import
        self.allow_creation(True)
        # Change the current layer
        self.iface.setActiveLayer(self.rfu.l_edge)
        self.iface.setActiveLayer(self.rfu.l_vertex)
        
        
    def rfu_on_reset(self):
        # Allow creation and import
        self.allow_creation(False)


    def tool_vtx_creator_on_triggered(self):
        # Set the layer l_vertex current
        self.iface.setActiveLayer(self.rfu.l_vertex)
        self.project.layerTreeRoot().findLayer(self.rfu.l_vertex.id()).setItemVisibilityChecked(True)
        self.canvas.refresh()
        # Check the editable mode
        if not self.rfu.l_vertex.isEditable():
            self.rfu.l_vertex.startEditing()
        
        if not self.rfu.dflt_ellips_acronym:
            self.rfu.selected_ellips_acronym = self.rfu.dflt_ellips_acronym

        dlg_vtx_creator = VertexCreator(
                            self.canvas,
                            self.project,
                            self.rfu.layers[0],
                            user=self.rfu.conn.user,
                            precision_class=self.rfu.precision_class,
                            ellips_acronym=self.rfu.ellips_acronym,
                            selected_ellips_acronym=self.rfu.selected_ellips_acronym,
                            typo_nature_som=self.rfu.typo_nature_som,
                            auth_creator=self.rfu.auth_creator,
                            tol_spt = self.rfu.tol_same_pt)
        
        dlg_vtx_creator.show()

        if not dlg_vtx_creator.exec_():
            return None


    def tool_edge_creator_on_triggered(self, checked=False):
        if not checked:
            self.edge_creator.close()
            self.edge_creator = None

        if checked:
            # Set the layer l_edge current
            self.iface.setActiveLayer(self.rfu.l_edge)
            self.project.layerTreeRoot().findLayer(self.rfu.l_edge.id()).setItemVisibilityChecked(True)
            self.canvas.refresh()
            # Check the editable mode
            if not self.rfu.l_edge.isEditable():
                self.rfu.l_edge.startEditing()
            
            self.edge_creator = EdgeCreator(
                                    self.iface,
                                    self.canvas,
                                    self.rfu.layers[0],
                                    self.rfu.layers[1],
                                    typo_nature_lim=self.rfu.typo_nature_lim,
                                    user=self.rfu.conn.user,
                                    auth_creator=self.rfu.auth_creator)

            self.edge_creator.setObjectName(r"EdgeCreatorDockWidget")
            self.edge_creator.destroyed.connect(self.on_edge_creator_destroyed)
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.edge_creator)


    def on_edge_creator_destroyed(self):

        self.edge_creator = None
        return self.action_edge_creator.setChecked(False)


    # Launch the import csv tool
    def tool_import_csvrfu(self):
        if self.rfu :
            self.csv2rfu_import = ImportCsvRfu(
                                    self.iface,
                                    self.canvas,
                                    self.project,
                                    self.rfu.layers[0],
                                    self.rfu.layers[1],
                                    user=self.rfu.conn.user,
                                    auth_creator=self.rfu.auth_creator,
                                    precision_class=self.rfu.precision_class,
                                    ellips_acronym=self.rfu.ellips_acronym,
                                    selected_ellips_acronym=self.rfu.selected_ellips_acronym,
                                    typo_nature_som=self.rfu.typo_nature_som,
                                    typo_nature_lim=self.rfu.typo_nature_lim,
                                    tol_spt=self.rfu.tol_same_pt)
            self.csv2rfu_import.import_file()
        else :
            QMessageBox.information(
                                    self.iface.mainWindow(), 
                                    tl_imp_canc, 
                                    txt_csvimp_norfu_canc)
    
    
    # Launch the import dxf tool
    def tool_import_dxf2rfu(self):
        if self.rfu :
            self.dxf2rfu_import = ImportDxf2Rfu(
                                    self.iface,
                                    self.canvas,
                                    self.project,
                                    self.rfu.layers[0],
                                    self.rfu.layers[1],
                                    user=self.rfu.conn.user,
                                    auth_creator=self.rfu.auth_creator,
                                    precision_class=self.rfu.precision_class,
                                    ellips_acronym=self.rfu.ellips_acronym,
                                    selected_ellips_acronym=self.rfu.selected_ellips_acronym,
                                    typo_nature_som=self.rfu.typo_nature_som,
                                    typo_nature_lim=self.rfu.typo_nature_lim,
                                    tol_spt=self.rfu.tol_same_pt)
            self.dxf2rfu_import.import_file()
        else :
            QMessageBox.information(
                                    self.iface.mainWindow(), 
                                    tl_imp_canc, 
                                    txt_dxfimp_norfu_canc)
    

    # Cut an old limit at the point of a new vertex
    def tool_cut_oldlimit(self):
        if self.rfu and self.rfu.layers[0]:
            # Set the layer l_vertex current
            self.iface.setActiveLayer(self.rfu.l_vertex)
            self.project.layerTreeRoot().findLayer(self.rfu.l_vertex.id()).setItemVisibilityChecked(True)
            self.canvas.refresh()
            # Check the editable mode
            if not self.rfu.l_vertex.isEditable():
                self.rfu.l_vertex.startEditing()
            self.tr_cut_oldlimit = CutOldLimit(
                                    self.canvas,
                                    self.project,
                                    self.rfu.layers[0],
                                    self.rfu.layers[1],)
            # # Modal window
            # self.tr_pt_to_plot.setWindowModality(Qt.ApplicationModal)
            self.tr_cut_oldlimit.show()
        else :
            QMessageBox.information(
                                    self.iface.mainWindow(), 
                                    tr_pttoplot_imp_msg[0], 
                                    tr_pttoplot_imp_msg[1])    
                            
                                    
    # Management of the new vertices to transform into plots
    def tool_transfo_pt_to_plot(self):
        if self.rfu and self.rfu.layers[0]:
            # Set the layer l_vertex current
            self.iface.setActiveLayer(self.rfu.l_vertex)
            self.project.layerTreeRoot().findLayer(self.rfu.l_vertex.id()).setItemVisibilityChecked(True)
            self.canvas.refresh()
            # Check the editable mode
            if not self.rfu.l_vertex.isEditable():
                self.rfu.l_vertex.startEditing()
            self.tr_pt_to_plot = TransfoPtToPlot(
                                    self.canvas,
                                    self.project,
                                    self.rfu.layers[0],
                                    self.rfu.layers[1],)
            # # Modal window
            # self.tr_pt_to_plot.setWindowModality(Qt.ApplicationModal)
            self.tr_pt_to_plot.dlg_show()
        else :
            QMessageBox.information(
                                    self.iface.mainWindow(), 
                                    tr_pttoplot_imp_msg[0], 
                                    tr_pttoplot_imp_msg[1])
                                    
                                      
    # Let the user choose a point to show the point plots
    def tool_select_pt_to_plot(self, type_fnc):
        
        self.plot_fnc_mode = type_fnc
        if self.conn and self.rfu and self.rfu.zone:
            # Prompt message
            self.iface.messageBar().pushMessage(
                plot_dif_txt[type_fnc][0], plot_dif_txt[type_fnc][1],
                Qgis.Info, duration=10)
            # Pointer to choose the vertex
            # Set the layer l_vertex current
            self.iface.setActiveLayer(self.rfu.l_vertex)
            self.project.layerTreeRoot().findLayer(self.rfu.l_vertex.id()).setItemVisibilityChecked(True)
            self.canvas.refresh()
            self.identify_pttoplot = QgsMapToolIdentifyFeature(self.canvas, self.rfu.l_vertex)
            self.identify_pttoplot.setCursor(QCursor(Qt.WhatsThisCursor))
            self.identify_pttoplot.featureIdentified.connect(self.pt_to_plot_identified)
            self.canvas.setMapTool(self.identify_pttoplot)
        
        
    # Prepare and show the point plots dlg
    def pt_to_plot_identified(self, pt_feat):
        # Select the point
        self.rfu.l_vertex.selectByIds([pt_feat.id()])
        id_node = pt_feat["@id_noeud"]   
        # Check the selected point is a RFU vertex
        if id_node:
            resp_plots = None
            # Get the pt plots infos
            resp = self.conn.get_ptplots(id_node, self.rfu.zone)
            resp_plots = resp.read()
            tree = ElementTree.fromstring(resp_plots)
            if resp.code != 200:
                # Catch the error specified by the API          
                elt_err = tree.find(r"./log")
                if elt_err.text:
                    msg = elt_err.text
                else:
                    # Error returned by the server (all other cases)
                    msg = str(resp_plots)
                # Display the error in a message box
                return QMessageBox.warning(self.iface.mainWindow(), msg_obt_det_imp, msg)
            else: 
                ptplot = tree.find(r"./sommet/determination")
                # Case of no plots
                if 'Message' in ptplot.attrib:
                    msg = ptplot.attrib["Message"]
                    QMessageBox.warning(self.iface.mainWindow(), msg_obt_det_imp, msg)
                else:
                    # DEBUG
                    # urlresp_to_file(resp_plots) 
                    
                    # Prepare and show the dlg
                    self.show_ptplots = ShowPtPlots(self.conn, self.rfu.zone, resp_plots, self.plot_fnc_mode, self.iface.mainWindow())
                    # Modal window
                    self.show_ptplots.setWindowModality(Qt.ApplicationModal)
                    self.show_ptplots.ptplotsNwPtSelect.connect(partial(self.tool_select_pt_to_plot, "info"))
                    self.show_ptplots.plots_show()
        # Case of selected point is not a RFU vertex
        else:
            QMessageBox.warning(self.iface.mainWindow(), plot_notrfusel_msg[0], plot_notrfusel_msg[1])


    # Lets appear the show capabilities dlg
    def tool_show_capabilities(self):
        resp_mycap = None
        resp_cap = None
        # Get C1 capabilities
        if self.conn :
            resp = self.conn.get_my_capabilities()
            resp_mycap = resp.read()
            if resp.code != 200:
                # Catch the error specified by the API
                tree = ElementTree.fromstring(resp_mycap)
                elt_err = tree.find(r"./log")
                if elt_err.text:
                    msg = elt_err.text
                else:
                    # Error returned by the server (all other cases)..
                    msg = str(resp_mycap)
                # Display the error in a message box
                return QMessageBox.warning(self.iface.mainWindow(), msg_obt_cap_imp, msg)
            if self.rfu and self.rfu.zone:
                resp = self.conn.get_capabilities(self.rfu.zone)
                resp_cap = resp.read()
                # DEBUG: Export response as a text file
                # urlresp_to_file(resp_ap)
                if resp.code != 200:
                    # Catch the error specified by the API
                    tree = ElementTree.fromstring(resp_cap)
                    elt_err = tree.find(r"./log")
                    if elt_err.text:
                        msg = elt_err.text
                    else:
                        # Error returned by the server (all other cases)
                        msg = str(resp_cap)
                    # Display the error in a message box
                    return QMessageBox.warning(self.iface.mainWindow(), msg_obt_cap_imp, msg)
            # Prepare and show the dlg
            self.show_capa = ShowCapabilities(resp_cap, resp_mycap)
            self.show_capa.show()
        else:
            # No connection: alert message
            return QMessageBox.warning(self.iface.mainWindow(), msg_obt_cap_imp, msg_obt_cap_ident)
        
        
    # Allow (or disallow) creation and import
    def allow_creation(self, state):
        self.action_vtx_creator.setEnabled(state)
        self.action_edge_creator.setEnabled(state)
        self.action_import_csv2rfu.setEnabled(state)
        self.action_import_dxf2rfu.setEnabled(state)
        self.action_cut_oldlimit.setEnabled(state)
        self.action_transfo_pt_to_plot.setEnabled(state)
        self.action_del_ptplot.setEnabled(state)
        self.action_show_ptplots.setEnabled(state)
