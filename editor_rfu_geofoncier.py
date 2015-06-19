#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os.path

from PyQt4.QtCore import qVersion
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtCore import QTranslator
from PyQt4.QtCore import QSettings
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QObject
from PyQt4.QtCore import SIGNAL
# from PyQt4.QtCore import QPyNullVariant
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QAction
from qgis.core import QgsMapLayerRegistry

import resources_rc
import tools
from rfu_connector import RFUDockWidget
from vertex_creator import VertexCreator
from edge_creator import EdgeCreator


class EditorRFUGeofoncier:

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface

        self.canvas = self.iface.mapCanvas()
        self.map_layer_registry = QgsMapLayerRegistry.instance()

        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Initialize locale
        locale = QSettings().value(r"locale/userLocale")[0:2]
        locale_path = os.path.join(
                self.plugin_dir, r"i18n",
                r"EditorRFUGeofoncier_{}.qm".format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > r"4.3.3":
                QCoreApplication.installTranslator(self.translator)

        self.rfu = None
        self.edge_creator = None

        # Activate 'On The Fly'
        self.canvas.mapRenderer().setProjectionsEnabled(True)

    def unload(self):

        # Remove the plugin menu item and icon..
        self.iface.removePluginMenu(u"&Géofoncier", self.action_connector)
        self.iface.removeToolBarIcon(self.action_connector)
        if self.iface:
            self.iface.removeDockWidget(self.rfu)

    def initGui(self):

        # Add tool bar..
        self.toolbar = self.iface.addToolBar(u"Éditeur RFU Géofoncier")
        self.toolbar.setObjectName(r"EditorRFUGeofoncierToolBar")

        # Create action(s)..

        self.action_connector = QAction(
            QIcon(r":/resources/btn_conn_rfu"),
            u"Connecteur RFU", self.iface.mainWindow())
        self.action_connector.setEnabled(True)
        self.action_connector.setCheckable(True)

        self.action_vtx_creator = QAction(
            QIcon(r":/resources/btn_add_vtx"),
            u"Nouveau nœud RFU", self.iface.mainWindow())
        self.action_vtx_creator.setEnabled(False)

        self.action_edge_creator = QAction(
            QIcon(r":/resources/btn_add_edge"),
            u"Nouvelle limite RFU", self.iface.mainWindow())
        self.action_edge_creator.setEnabled(False)
        self.action_edge_creator.setCheckable(True)

        # Then add action(s) to the tool bar..
        self.toolbar.addActions([self.action_connector,
                                 self.action_vtx_creator,
                                 self.action_edge_creator])

        # Manage signals..
        self.iface.currentLayerChanged.connect(self.on_toggled)
        # self.canvas.mapToolSet.connect(self.deactivate_tool)
        self.map_layer_registry.layersRemoved.connect(self.on_layers_removed)

        self.action_connector.triggered[bool].connect(self.tool_rfu_on_triggered)
        self.action_vtx_creator.triggered.connect(self.tool_vtx_creator_on_triggered)
        self.action_edge_creator.triggered[bool].connect(self.tool_edge_creator_on_triggered)

        # Initialize current layer to None (See switch_editing())..
        self.current_layer = None

    # On iface Signals
    # ================

    def on_toggled(self):

        layer = self.canvas.currentLayer()
        if not layer:
            return

        if layer.isEditable() and layer == self.rfu.layers[0]:
            self.switch_editing(layer)
            self.action_vtx_creator.setEnabled(True)
            self.action_edge_creator.setEnabled(False)
            QObject.connect(layer, SIGNAL(r"editingStopped()"), self.on_toggled)
            QObject.disconnect(layer, SIGNAL(r"editingStarted()"), self.on_toggled)

        elif layer.isEditable() and layer == self.rfu.layers[1]:
            self.switch_editing(layer)
            self.action_vtx_creator.setEnabled(False)
            self.action_edge_creator.setEnabled(True)
            QObject.connect(layer, SIGNAL(r"editingStopped()"), self.on_toggled)
            QObject.disconnect(layer, SIGNAL(r"editingStarted()"), self.on_toggled)

        else:
            self.action_vtx_creator.setEnabled(False)
            self.action_edge_creator.setEnabled(False)
            QObject.connect(layer, SIGNAL(r"editingStarted()"), self.on_toggled)
            QObject.disconnect(layer, SIGNAL(r"editingStopped()"), self.on_toggled)

    def switch_editing(self, layer):

        if self.current_layer is not None:
            old_layer = self.current_layer
            old_layer.committedFeaturesAdded.disconnect(self.on_committed_features_added)
            old_layer.committedFeaturesRemoved.disconnect(self.on_committed_features_removed)
            # old_layer.featureAdded.disconnect(self.on_feature_added)
            old_layer.attributeValueChanged.disconnect(self.on_attribute_value_changed)
            old_layer.geometryChanged.disconnect(self.on_geometry_changed)

        self.current_layer = layer
        layer.committedFeaturesAdded.connect(self.on_committed_features_added)
        layer.committedFeaturesRemoved.connect(self.on_committed_features_removed)
        # layer.featureAdded.connect(self.on_feature_added)
        layer.attributeValueChanged.connect(self.on_attribute_value_changed)
        layer.geometryChanged.connect(self.on_geometry_changed)

    def on_committed_features_added(self, layer_id, features):
        self.rfu.add_features(layer_id, features)

    def on_committed_features_removed(self, layer_id, ft_id_list):
        self.rfu.remove_features(layer_id, ft_id_list)

    # def on_feature_added(self, fid):
        # feature = tools.get_feature_by_id(self.current_layer, fid)
        # self.rfu.add_feature(self.current_layer.id(), feature)

    def on_geometry_changed(self, fid, geom):
        # TODO: Forbidden
        pass

    def on_attribute_value_changed(self, fid, field_idx, value):
        feature = tools.get_feature_by_id(self.current_layer, fid)
        self.rfu.modify_feature(self.current_layer.id(), feature)

    # On map layer registry signals
    # =============================

    def on_layers_removed(self, layers):
        self.current_layer = None

    # On action signals
    # =================

    def tool_rfu_on_triggered(self, checked):

        if checked and not self.rfu:
            self.rfu = RFUDockWidget(self.canvas, self.map_layer_registry)
            self.rfu.setObjectName(r"RFUDockWidget")
            self.iface.addDockWidget(Qt.TopDockWidgetArea, self.rfu)
            self.rfu.closed.connect(self.rfu_on_closed)

        if checked and self.rfu:
            self.rfu.show()

        if not checked:
            self.rfu.hide()

    def rfu_on_closed(self):

        self.action_connector.setChecked(False)

    def tool_vtx_creator_on_triggered(self):

        dlg_vtx_creator = VertexCreator(
                            self.canvas,
                            self.rfu.layers[0],
                            user=self.rfu.conn.user,
                            precision_class=self.rfu.precision_class,
                            ellips_acronym=self.rfu.ellips_acronym,
                            dflt_ellips_acronym=self.rfu.dflt_ellips_acronym,
                            nature=self.rfu.nature,
                            auth_creator=self.rfu.auth_creator)

        dlg_vtx_creator.show()

        if not dlg_vtx_creator.exec_():
            return None

    def tool_edge_creator_on_triggered(self, checked=False):

        if not checked:
            self.edge_creator.close()
            self.edge_creator = None

        if checked:
            self.edge_creator = EdgeCreator(
                                    self.canvas,
                                    self.rfu.layers[0],
                                    self.rfu.layers[1],
                                    user=self.rfu.conn.user,
                                    auth_creator=self.rfu.auth_creator)

            self.edge_creator.setObjectName(r"EdgeCreatorDockWidget")
            self.edge_creator.destroyed.connect(self.on_edge_creator_destroyed)
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.edge_creator)

    def on_edge_creator_destroyed(self):

        self.edge_creator = None
        return self.action_edge_creator.setChecked(False)
