#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os
import re
import xml.etree.ElementTree as EltTree
# from datetime import datetime
from urlparse import urlparse
from urlparse import parse_qs

from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import QVariant
# from PyQt4.QtCore import QDateTime
# from PyQt4.QtCore import QDate
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QDockWidget
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QProgressBar
from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsFillSymbolV2
from qgis.core import QgsRectangle
# from qgis.core import QgsProject
# from qgis.core import QgsSnapper
# from qgis.core import QgsTolerance
from qgis.core import QgsVectorLayer
from qgis.core import QgsMarkerSymbolV2
from qgis.core import QgsLineSymbolV2
from qgis.core import QgsRuleBasedRendererV2
from qgis.core import QgsLabel
from qgis.core import QgsField
from qgis.core import QgsFeature
from qgis.core import QgsGeometry
from qgis.core import QgsExpression
from qgis.core import QgsPalLayerSettings
from qgis.core import QgsSingleSymbolRendererV2
from qgis.core import QgsInvertedPolygonRenderer
from qgis.gui import QgsMapCanvasLayer
from qgis.gui import QgsMessageBar

import tools
from login import GeoFoncierAPILogin


gui_dckwdgt_rfu_connector, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), r"gui/dckwdgt_rfu_connector.ui"))


class RFUDockWidget(QDockWidget, gui_dckwdgt_rfu_connector):

    closed = pyqtSignal()

    def __init__(self, iface, canvas, map_layer_registry, conn=None, parent=None):

        super(RFUDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self.canvas = canvas
        self.map_layer_registry = map_layer_registry
        self.conn = conn
        self.zone = None
        self.precision_class = []
        self.ellips_acronym = []
        self.dflt_ellips_acronym = None
        self.selected_ellips_acronym = None
        self.nature = []
        self.auth_creator = []

        self.url = None

        self.l_vertex = None
        self.l_edge = None
        self.layers = [self.l_vertex, self.l_edge]

        # Initialize dicts which contains data RFU modif..
        # self.edges_added_temp = {}
        # self.vertices_added_temp = {}
        self.edges_added = {}
        self.vertices_added = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}

        self.downloadPushButton.clicked.connect(self.on_downloaded)
        self.permalinkLineEdit.returnPressed.connect(self.on_downloaded)
        self.projComboBox.currentIndexChanged.connect(self.set_destination_crs)

    def closeEvent(self, event):

        self.closed.emit()

    def set_destination_crs(self, j):

        epsg = 4326 # by default
        for i, e in enumerate(self.ellips_acronym):
            if i == j:
                self.selected_ellips_acronym = e[0]
                epsg = int(e[1])
                continue

        crs = QgsCoordinateReferenceSystem(epsg, QgsCoordinateReferenceSystem.EpsgCrsId)
        self.canvas.setDestinationCrs(crs)
        self.canvas.zoomToFullExtent()

    #def open_connection(self):
    #    """Call GeoFoncierAPILogin() ie. the `Sign In` DialogBox.
    #    If accepted -> return a new APIClient() obj.
    #
    #    """
    #    dlg_login = GeoFoncierAPILogin()
    #    dlg_login.show()
    #
    #    # Test if failed..
    #    if not dlg_login.exec_():
    #        return None
    #
    #    # Then..
    #    return dlg_login.conn

    def on_downloaded(self):

        # Create message
        widget = self.iface.messageBar().createMessage(u"Géofoncier", u"Téléchargement du RFU.")
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(2)
        widget.layout().addWidget(progress_bar)
        self.iface.messageBar().pushWidget(widget, QgsMessageBar.WARNING)

        progress_bar.setValue(1)

        # Download data
        self.download()

        self.iface.messageBar().clearWidgets()

    def download(self, url=None):

        if not url:
            #url = u"https://pro.geofoncier.fr/index.php?&centre=-196406,5983255&context=metropole"
            url = self.permalinkLineEdit.text()
        if not url:
            msg = u"Veuillez renseigner le permalien."
            return QMessageBox.warning(self, r"Warning", msg)

        self.url = url

        # Connect to API if none..
        #if not self.conn:
        #    self.conn = self.open_connection()
        #if not self.conn:
        #    return None

        # Test if permalink is valid (&centre and &context are mandatory)..
        pattern = r"^(https?:\/\/(\w+[\w\-\.\:\/])+)\?((\&+)?(context|centre|\w+)\=?([\w\-\.\:\,]+?)?)+(\&+)?$"
        if not re.match(pattern, self.url):
            msg = u"Le permalien n'est pas valide."
            return QMessageBox.warning(self, r"Warning", msg)

        # Extract params from url..
        params = parse_qs(urlparse(self.url).query)

        # Extract zone (&context)..
        self.zone = str(params[r"context"][0])

        # TODO: Récupèrer cette liste depuis l'API..
        auth_zone = [r"metropole", r"antilles",
                     r"guyane", r"reunion", r"mayotte"]

        if self.zone not in auth_zone:
            msg = u"Le territoire indiqué ‘%s’ est incorrect." % self.zone
            return QMessageBox.warning(self, r"Warning", msg)

        # Check if XY are valid..
        center = params[r"centre"][0]
        if not re.match(r"^\-?\d+,\-?\d+$", center):
            msg = u"Les coordonnées XY du centre sont incorrectes."
            return QMessageBox.warning(self, r"Warning", msg)

        # Extract XY (&centre)..
        xcenter = int(center.split(r",")[0])
        ycenter = int(center.split(r",")[1])

        # Compute the bbox..
        xmin = xcenter - self.conn.extract_lim / 2
        xmax = xcenter + self.conn.extract_lim / 2
        ymin = ycenter - self.conn.extract_lim / 2
        ymax = ycenter + self.conn.extract_lim / 2

        # Transform coordinates in WGS84..
        bbox = tools.reproj(QgsRectangle(xmin, ymin, xmax, ymax), 3857, 4326)

        # Extract RFU (Send the request)..
        resp = self.conn.extraction(bbox.xMinimum(), bbox.yMinimum(),
                                    bbox.xMaximum(), bbox.yMaximum())

        if resp.code != 200:
            return QMessageBox.warning(self, r"Warning", resp.read())

        tree = EltTree.fromstring(resp.read())

        # Check if error
        err = tree.find(r"./erreur")
        if err:
            return QMessageBox.warning(self, r"Warning", err.text)

        # isvalid = self.extraction_isvalid(xml)
        # if isvalid is False:
        #     msg = u"L'extraction RFU n'est pas valide."
        #     return QMessageBox.warning(self, r"Warning", msg)

        # Create layers "Masque d'extraction"
        self.l_bbox = QgsVectorLayer(r"Polygon?crs=epsg:4326&index=yes",
                                     u"Zone de travail", r"memory")
        p_bbox = self.l_bbox.dataProvider()

        simple_symbol = QgsFillSymbolV2.createSimple({
                                r"color": r"116,97,87,255",
                                r"style": r"b_diagonal",
                                r"outline_style": r"no"})

        renderer_bbox = QgsInvertedPolygonRenderer(QgsSingleSymbolRendererV2(simple_symbol))

        self.l_bbox.setRendererV2(renderer_bbox)

        ft_bbox = QgsFeature()
        ft_bbox.setGeometry(QgsGeometry.fromRect(QgsRectangle(bbox.xMinimum(), bbox.yMinimum(),
                                                              bbox.xMaximum(), bbox.yMaximum())))
        p_bbox.addFeatures([ft_bbox])

        self.l_bbox.updateFields()
        self.l_bbox.updateExtents()

        # Create layers..
        self.layers = self.extract_layers(tree)
        self.l_vertex = self.layers[0]
        self.l_edge = self.layers[1]

        # Add layer to the registry
        self.map_layer_registry.addMapLayers([self.l_vertex, self.l_edge, self.l_bbox])

        # Set the map canvas layer set
        self.canvas.setLayerSet([QgsMapCanvasLayer(self.l_vertex),
                                 QgsMapCanvasLayer(self.l_edge),
                                 QgsMapCanvasLayer(self.l_bbox)])

        # Set extent
        self.canvas.setExtent(QgsRectangle(bbox.xMinimum(), bbox.yMinimum(),
                                           bbox.xMaximum(), bbox.yMaximum()))

        # Activate snapping..
        # for layer in self.layers:
        #    QgsProject.instance().setSnapSettingsForLayer(
        #         layer.id(), True, QgsSnapper.SnapToVertexAndSegment,
        #         QgsTolerance.Pixels, 8, True)

        self.features_vertex_backed_up = \
            dict((ft[r"fid"], ft) for ft in self.get_features(self.layers[0]))
        self.features_edge_backed_up = \
            dict((ft[r"fid"], ft) for ft in self.get_features(self.layers[1]))

        # Get Capabitilies
        resp = self.conn.get_capabilities(self.zone)

        if resp.code != 200:
            return QMessageBox.warning(self, r"Warning", resp.read())

        tree = EltTree.fromstring(resp.read())

        err = tree.find(r"./erreur")
        if err:
            return QMessageBox.warning(self, r"Warning", err.text)

        for entry in tree.findall(r"./classe_rattachement/classe"):
            t = (entry.attrib[r"som_precision_rattachement"], entry.text)
            self.precision_class.append(t)

        for entry in tree.findall(r"./representation_plane_sommet_autorise/representation_plane_sommet"):
            t = (entry.attrib[r"som_representation_plane"], entry.attrib[r"epsg_crs_id"], entry.text)
            self.ellips_acronym.append(t)

        for entry in tree.findall(r"./nature_sommet_conseille/nature"):
            self.nature.append(entry.text)

        for entry in tree.findall(r"./som_ge_createur_autorise/som_ge_createur"):
            t = (entry.attrib[r"num_ge"], entry.text)
            self.auth_creator.append(t)

        try:
            ft = next(ft for ft in self.layers[0].getFeatures())
            ft_attrib = tools.attrib_as_kv(ft.fields(), ft.attributes())
            self.dflt_ellips_acronym = ft_attrib[r"som_representation_plane"]
        except:
            self.dflt_ellips_acronym = None

        for i, e in enumerate(self.ellips_acronym):

            self.projComboBox.addItem(e[2])

            if not self.dflt_ellips_acronym:
                continue

            if self.dflt_ellips_acronym == e[0]:

                # Check projection in combobox
                self.projComboBox.setCurrentIndex(i)

                # Activate 'On The Fly'
                #self.canvas.mapRenderer().setProjectionsEnabled(True)
                self.canvas.setCrsTransformEnabled(True)

                # Then change the CRS in canvas
                crs = QgsCoordinateReferenceSystem(int(e[1]), QgsCoordinateReferenceSystem.EpsgCrsId)
                self.canvas.setDestinationCrs(crs)

        # Then, start editing mode..
        for layer in self.layers:
            if not layer.isEditable():
                layer.startEditing()

        self.projComboBox.setDisabled(False)

        self.permalinkLineEdit.setDisabled(True)
        self.downloadPushButton.setDisabled(True)
        self.resetPushButton.setDisabled(False)
        self.uploadPushButton.setDisabled(False)

        self.downloadPushButton.clicked.disconnect(self.on_downloaded)
        self.permalinkLineEdit.returnPressed.disconnect(self.on_downloaded)
        self.resetPushButton.clicked.connect(self.on_reset)
        self.uploadPushButton.clicked.connect(self.on_uploaded)

    def on_reset(self):

        # Ensure that the action is intentional..
        msg = (u"Cette action est irreversible. "
               u"Toute modification sera perdue. "
               u"Êtes-vous sûr de vouloir réinitialiser l'outil ?")
        resp = QMessageBox.question(self, r"Question", msg,
                                    QMessageBox.Yes, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return False

        res = self.reset()
        if res != True:
            return None

    def reset(self):
        """Remove RFU layers."""

        # Remove RFU layers..
        try:
            #self.map_layer_registry.removeMapLayers([l.id() for l in self.layers])
            self.map_layer_registry.removeMapLayers([
                            self.l_vertex.id(), self.l_edge.id(), self.l_bbox.id()])
        except:
            return

        # Reset variable..
        self.precision_class = []
        self.ellips_acronym = []
        self.dflt_ellips_acronym = None
        self.nature = []
        self.auth_creator = []
        self.l_vertex = None
        self.l_edge = None
        self.layers = [self.l_vertex, self.l_edge]
        self.edges_added = {}
        self.vertices_added = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}

        # Reset ComboBox which contains projections authorized..
        self.projComboBox.clear()
        self.projComboBox.setDisabled(True)

        self.permalinkLineEdit.clear()
        self.permalinkLineEdit.setDisabled(False)
        self.permalinkLineEdit.returnPressed.connect(self.on_downloaded)

        self.downloadPushButton.setDisabled(False)
        self.downloadPushButton.clicked.connect(self.on_downloaded)

        self.resetPushButton.setDisabled(True)
        self.resetPushButton.clicked.disconnect(self.on_reset)

        self.uploadPushButton.setDisabled(True)
        self.uploadPushButton.clicked.disconnect(self.on_uploaded)

        return True

    def on_uploaded(self):

        # Create message
        widget = self.iface.messageBar().createMessage(u"Géofoncier", u"Envoi des modifications.")
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(3)
        widget.layout().addWidget(progress_bar)
        self.iface.messageBar().pushWidget(widget, QgsMessageBar.WARNING)

        # Ensure that the action is intentional..
        msg = (u"Vous êtes sur le point de soumettre "
               u"les modifications au serveur GéoFoncier. "
               u"Souhaitez-vous poursuivre cette action ?")

        resp = QMessageBox.question(self, r"Question", msg,
                                    QMessageBox.Yes, QMessageBox.No)
        if resp != QMessageBox.Yes:
            self.iface.messageBar().clearWidgets()
            return False

        progress_bar.setValue(1)
        # Stop editing mode..
        for layer in self.layers:
            if layer.isEditable():
                #msg = (u"Veuillez fermer le mode d'édition et valider "
                #       u"vos modification avant de poursuivre.")
                #return QMessageBox.warning(self, r"Warning", msg)
                layer.commitChanges()

        if (self.edges_added
                or self.vertices_added
                or self.edges_removed
                or self.vertices_removed
                or self.edges_modified
                or self.vertices_modified):
            pass
        else:
            # Nothing to do..
            self.iface.messageBar().clearWidgets()
            for layer in self.layers:
                if not layer.isEditable():
                    layer.startEditing()
            msg = (u"Aucune modification des données n'est détecté.")
            return QMessageBox.warning(self, r"Warning", msg)

        progress_bar.setValue(2)
        ul = self.upload()
        if ul != True:
            self.iface.messageBar().clearWidgets()
            return None

        #for layer in self.layers:
        #    if not layer.isEditable():
        #        layer.startEditing()

        #QMessageBox.information(
        #            self, u"Information",
        #            u"Les modifications du RFU sont enregistrées.")

        res = self.reset()
        if res != True:
            self.iface.messageBar().clearWidgets()
            return None

        self.download(url=self.url)
        self.canvas.zoomToFullExtent()

        self.iface.messageBar().clearWidgets()

        # self.permalinkLineEdit.setDisabled(True)
        # self.downloadPushButton.setDisabled(True)
        # self.resetPushButton.setDisabled(False)
        # self.uploadPushButton.setDisabled(False)

        # self.downloadPushButton.clicked.disconnect(self.on_downloaded)
        # self.permalinkLineEdit.returnPressed.disconnect(self.on_downloaded)
        # self.resetPushButton.clicked.connect(self.on_reset)
        # self.uploadPushButton.clicked.connect(self.on_uploaded)

    def upload(self):
        """Upload data to Géofoncier REST API."""

        root = EltTree.Element(r"rfu")

        if self.vertices_added:
            for fid in self.vertices_added:
                tools.xml_subelt_creator(root, u"sommet",
                                         data=self.vertices_added[fid],
                                         action=r"create")

        if self.edges_added:
            for fid in self.edges_added:
                tools.xml_subelt_creator(root, u"limite",
                                         data=self.edges_added[fid],
                                         action=r"create")

        if self.vertices_removed:
            for fid in self.vertices_removed:
                tools.xml_subelt_creator(root, u"sommet",
                                         data=self.vertices_removed[fid],
                                         action=r"delete")

        if self.edges_removed:
            for fid in self.edges_removed:
                tools.xml_subelt_creator(root, u"limite",
                                         data=self.edges_removed[fid],
                                         action=r"delete")

        if self.vertices_modified:
            for fid in self.vertices_modified:
                tools.xml_subelt_creator(root, u"sommet",
                                         data=self.vertices_modified[fid],
                                         action=r"update")

        if self.edges_modified:
            for fid in self.edges_modified:
                tools.xml_subelt_creator(root, u"limite",
                                         data=self.edges_modified[fid],
                                         action=r"update")

        # Open a new Changeset..
        opencs = self.conn.open_changeset(self.zone)

        if opencs.code != 200:
            return QMessageBox.warning(self, r"Warning", opencs.read())

        tree = EltTree.fromstring(opencs.read())

        err = tree.find(r"./erreur")
        if err:
            return QMessageBox.warning(self, r"Warning", err.text)

        treeterator = tree.getiterator(tag=r"changeset")
        if len(treeterator) != 1:
            # TODO
            return QMessageBox.warning(self, r"Warning", u"Une erreur est survenue.")

        changeset_id = treeterator[0].attrib[r"id"]
        root.attrib[r"changeset"] = changeset_id

        # Send data..
        edit = self.conn.edit(self.zone, EltTree.tostring(root))
        if edit.code != 200:
            return QMessageBox.warning(self, r"Warning", edit.read())

        tree = EltTree.fromstring(edit.read())
        err = tree.find(r"./erreur")
        if err:
            # Then display the error in a message box..
            return QMessageBox.warning(self, r"Warning", err.text)

        # Returns log info..
        msgs_log = []
        for log in tree.iter(r"log"):
            msgs_log.append(u"%s: %s" % (log.attrib[u"type"], log.text))
        QMessageBox.information(self, r"Information", u"\r".join(msgs_log))

        # Close the changeset..
        close_changeset = self.conn.close_changeset(self.zone, changeset_id)
        if close_changeset.code != 200:
            return QMessageBox.warning(self, r"Warning", close_changeset.read())

        tree = EltTree.fromstring(close_changeset.read())
        err = tree.find(r"./erreur")
        if err:
            # Then display the error in a message box..
            return QMessageBox.warning(self, r"Warning", err.text)

        # Reset all..
        self.edges_added = {}
        self.vertices_added = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}

        return True

    def extract_layers(self, tree):
        """Return a list of RFU layers."""

        # Create vector layers..
        l_vertex = QgsVectorLayer(r"Point?crs=epsg:4326&index=yes",
                                  u"Sommet RFU", r"memory")
        l_edge = QgsVectorLayer(r"LineString?crs=epsg:4326&index=yes",
                                u"Limite RFU", r"memory")

        p_vertex = l_vertex.dataProvider()
        p_edge = l_edge.dataProvider()

        # Define default style renderer..

        renderer_vertex = QgsRuleBasedRendererV2(QgsMarkerSymbolV2())
        vertex_root_rule = renderer_vertex.rootRule()
        vertex_rules = (
            (
                 (u"Borne, Borne à puce, Pierre, Piquet, Clou, Broche"),
                 (u"$id >= 0 AND \"som_nature\" IN ('Borne',"
                  u"'Borne à puce', 'Pierre', 'Piquet', 'Clou', 'Broche')"),
                 r"#EC0000", 2.2
            ), (
                 (u"Axe cours d'eau, Axe fossé, Haut de talus, Pied de talus"),
                 (u"$id >= 0 AND \"som_nature\" IN ('Axe cours d\'\'eau',"
                  u"'Axe fossé', 'Haut de talus', 'Pied de talus')"),
                 r"#EE8012", 2.2
            ), (
                 (u"Angle de bâtiment, Axe de mur, Angle de mur, "
                  u"Angle de clôture, Pylône et toute autre valeur"),
                 (u"$id >= 0 AND \"som_nature\" NOT IN ('Borne',"
                  u"'Borne à puce', 'Pierre', 'Piquet', 'Clou', 'Broche',"
                  u"'Axe cours d\'\'eau', 'Axe fossé', 'Haut de talus',"
                  u"'Pied de talus')"),
                 r"#9784EC", 2.2
            ), (
                u"Temporaire", r"$id < 0", "cyan", 2.4
            ))

        for label, expression, color, size in vertex_rules:
            rule = vertex_root_rule.children()[0].clone()
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().setColor(QColor(color))
            rule.symbol().setSize(size)
            vertex_root_rule.appendChild(rule)

        vertex_root_rule.removeChildAt(0)
        l_vertex.setRendererV2(renderer_vertex)

        renderer_edge = QgsRuleBasedRendererV2(QgsLineSymbolV2())
        edge_root_rule = renderer_edge.rootRule()
        edge_rules = ((r"Limite", r"$id >= 0", "#0A0AFF", 0.5),
                      (r"Temporaire", r"$id < 0", "cyan", 1))

        for label, expression, color, width in edge_rules:
            rule = edge_root_rule.children()[0].clone()
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().setColor(QColor(color))
            rule.symbol().setWidth(width)
            edge_root_rule.appendChild(rule)

        edge_root_rule.removeChildAt(0)
        l_edge.setRendererV2(renderer_edge)

        # Add fields..
        p_vertex.addAttributes([
                    QgsField(r"@id_noeud", QVariant.Int),
                    # QgsField(r"@changeset", QVariant.Int),
                    # QgsField(r"@timestamp", QVariant.Date),
                    QgsField(r"@version", QVariant.Int),
                    QgsField(r"som_ge_createur", QVariant.String),
                    QgsField(r"som_nature", QVariant.String),
                    QgsField(r"som_precision_rattachement", QVariant.Int),
                    QgsField(r"som_coord_est", QVariant.Double),
                    QgsField(r"som_coord_nord", QVariant.Double),
                    QgsField(r"som_representation_plane", QVariant.String),
                    # QgsField(r"date_creation", QVariant.Date)
                    ])

        p_edge.addAttributes([
                    QgsField(r"@id_arc", QVariant.Int),
                    # QgsField(r"@id_noeud_debut", QVariant.Int),
                    # QgsField(r"@id_noeud_fin", QVariant.Int),
                    # QgsField(r"@changeset", QVariant.Int),
                    # QgsField(r"@timestamp", QVariant.Date),
                    QgsField(r"@version", QVariant.Int),
                    QgsField(r"lim_ge_createur", QVariant.String),
                    # QgsField(r"lim_date_creation", QVariant.Date)
                    ])

        # Add features from xml tree..
        # ..to vertex layer..
        fts_vertex = []
        for e in tree.findall(r"sommet"):

            ft_vertex = QgsFeature()
            ft_vertex.setGeometry(QgsGeometry.fromWkt(e.attrib[r"geometrie"]))

            _id_noeud = int(e.attrib[r"id_noeud"])
            # _changeset = int(e.attrib[r"changeset"])
            # _timestamp = QDateTime(datetime.strptime(
            #                 e.attrib[r"timestamp"], r"%Y-%m-%d %H:%M:%S.%f"))
            _version = int(e.attrib[r"version"])
            som_ge_createur = unicode(e.find(r"./som_ge_createur").text)
            som_nature = unicode(e.find(r"./som_nature").text)
            som_prec_rattcht = int(e.find(r"./som_precision_rattachement").text)
            som_coord_est = float(e.find(r"./som_coord_est").text)
            som_coord_nord = float(e.find(r"./som_coord_nord").text)
            som_repres_plane = unicode(e.find(r"./som_representation_plane").text)
            # som_date_creation = QDate(datetime.strptime(
            #                         e.find(r"./som_date_creation").text, r"%Y-%m-%d").date())

            ft_vertex.setAttributes([
                        _id_noeud,
                        # _changeset,
                        # _timestamp,
                        _version,
                        som_ge_createur,
                        som_nature,
                        som_prec_rattcht,
                        som_coord_est,
                        som_coord_nord,
                        som_repres_plane,
                        # som_date_creation
                        ])

            fts_vertex.append(ft_vertex)

        # ..to edge layer..
        fts_edge = []
        for e in tree.findall(r"limite"):

            ft_edge = QgsFeature()
            ft_edge.setGeometry(QgsGeometry.fromWkt(e.attrib[r"geometrie"]))

            _id_arc = int(e.attrib[r"id_arc"])
            # _id_noeud_debut = int(e.attrib[r"id_noeud_debut"])
            # _id_noeud_fin = int(e.attrib[r"id_noeud_fin"])
            # _changeset = int(e.attrib[r"changeset"])
            # _timestamp = QDateTime(datetime.strptime(
            #                 e.attrib[r"timestamp"], r"%Y-%m-%d %H:%M:%S.%f"))
            _version = int(e.attrib[r"version"])
            lim_ge_createur = unicode(e.find(r"./lim_ge_createur").text)
            # lim_date_creation = QDate(datetime.strptime(
            #                        e.find(r"./lim_date_creation").text, r"%Y-%m-%d").date())

            ft_edge.setAttributes([
                        _id_arc,
                        # _id_noeud_debut,
                        # _id_noeud_fin,
                        # _changeset,
                        # _timestamp,
                        _version,
                        lim_ge_createur,
                        # lim_date_creation
                        ])

            fts_edge.append(ft_edge)

        # Add features to layers..
        p_vertex.addFeatures(fts_vertex)
        p_edge.addFeatures(fts_edge)

        # Update fields..
        l_vertex.updateFields()
        l_edge.updateFields()

        # Update layer's extent..
        l_vertex.updateExtents()
        l_edge.updateExtents()

        # Check if valid..
        if not l_vertex.isValid() or not l_edge.isValid():
            msg = u"Une erreur est survenue lors du chargement de la couche."
            return QMessageBox.warning(self, r"Warning", msg)

        # Set labelling...
        palyr = QgsPalLayerSettings()
        palyr.enabled = True
        # palyr.readFromLayer(l_vertex)
        palyr.fieldName = r"$id"  # Expression $id
        palyr.placement = 1  # ::OverPoint
        palyr.quadOffset = 2  # ::QuadrantAboveRight
        palyr.setDataDefinedProperty(80, True, True, r"1", "")  # ::OffsetUnits -> ::MM
        palyr.xOffset = 2.0
        palyr.yOffset = -1.0
        palyr.writeToLayer(l_vertex)

        # Then return layers..
        return [l_vertex, l_edge]

    def get_features(self, layer):

        features = []
        for ft in layer.getFeatures():
            attributes = tools.attrib_as_kv(ft.fields(), ft.attributes())
            attributes[r"fid"] = ft.id()
            features.append(attributes)

        return features

    def remove_features(self, layer_id, fids):

        for fid in fids:

            if layer_id == self.l_edge.id() and fid in self.features_edge_backed_up:
                self.edges_removed[fid] = self.features_edge_backed_up[fid]

            if layer_id == self.l_vertex.id() and fid in self.features_vertex_backed_up:
                self.vertices_removed[fid] = self.features_vertex_backed_up[fid]

    def add_features(self, layer_id, features):

        for ft in features:

            attrib = tools.attrib_as_kv(
                        ft.fields(), ft.attributes(), qgsgeom=ft.geometry())

            if layer_id == self.l_vertex.id():
                self.vertices_added[ft.id()] = attrib

            if layer_id == self.l_edge.id():
                self.edges_added[ft.id()] = attrib

    def modify_feature(self, layer_id, feature, qgsgeom=None):

        if qgsgeom:
            f = tools.attrib_as_kv(
                        feature.fields(), feature.attributes(), qgsgeom=qgsgeom)
        else:
            f = tools.attrib_as_kv(feature.fields(), feature.attributes())

        if self.l_edge.id() == layer_id:
            if feature.id() not in self.features_edge_backed_up:
                return
            self.edges_modified[feature.id()] = f

        if self.l_vertex.id() == layer_id:
            if feature.id() not in self.features_vertex_backed_up:
                return
            self.vertices_modified[feature.id()] = f
