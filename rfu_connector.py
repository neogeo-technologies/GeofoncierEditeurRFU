#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import os
import re
import xml.etree.ElementTree as EltTree
from urlparse import urlparse
from urlparse import parse_qs

from PyQt4 import uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QDockWidget
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QProgressBar

from PyQt4.QtGui import QInputDialog
from PyQt4.QtGui import QLineEdit

from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsFillSymbolV2
from qgis.core import QgsRectangle
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
    downloaded = pyqtSignal()

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

        # Initialize dicts which contains changed datasets
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

    def on_downloaded(self):

        widget = self.iface.messageBar().createMessage(u"Géofoncier", u"Téléchargement du RFU.")

        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(2)
        widget.layout().addWidget(progress_bar)

        self.iface.messageBar().pushWidget(widget, QgsMessageBar.WARNING)
        progress_bar.setValue(1)

        # https://pro.geofoncier.fr/index.php?&centre=-196406,5983255&context=metropole
        url = self.permalinkLineEdit.text()
        if not url:
            return self.abort_action(msg=u"Veuillez renseigner le permalien.")
        self.url = url

        try:
            self.download(self.url)
        except Exception as e:
            return self.abort_action(msg=e.message)

        progress_bar.setValue(2)
        self.iface.messageBar().clearWidgets()

        return

    def on_reset(self):

        # Ensure that the action is intentional
        msg = (u"Cette action est irreversible. "
               u"Toute modification sera perdue. "
               u"Êtes-vous sûr de vouloir réinitialiser l'outil ?")
        resp = QMessageBox.question(self, r"Question", msg,
                                    QMessageBox.Yes, QMessageBox.No)
        if resp == QMessageBox.Yes:
            self.reset()

        return

    def on_uploaded(self):

        # Create message
        widget = self.iface.messageBar().createMessage(u"Géofoncier", u"Envoi des modifications.")
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(3)
        widget.layout().addWidget(progress_bar)
        self.iface.messageBar().pushWidget(widget, QgsMessageBar.WARNING)
        progress_bar.setValue(1)

        # Stop editing mode
        for layer in self.layers:
            if layer.isEditable():
                layer.commitChanges()

        # Check if dataset changes
        if (self.edges_added
                or self.vertices_added
                or self.edges_removed
                or self.vertices_removed
                or self.edges_modified
                or self.vertices_modified):
            pass
        else:
            return self.abort_action(msg=u"Aucune modification des données n'est détecté.")

        enr_ref_dossier, ok = QInputDialog.getText(
                                self, u"Référence de dossier",
                                u"Vous êtes sur le point de soumettre\n"
                                u"les modifications au serveur Géofoncier.\n"
                                u"Veuillez renseigner la référence du dossier.")
        if not ok:
            return self.abort_action()

        if enr_ref_dossier:

            dossiers = self.conn.dossiersoge_dossiers(self.zone, enr_ref_dossier)
            if dossiers.code != 200:
                return self.abort_action(msg=dossiers.read())

            tree = EltTree.fromstring(dossiers.read())

            # Check if exception
            err = tree.find(r"./erreur")
            if err:
                return self.abort_action(msg=err.text)

            nb_dossiers = int(tree.find(r"./dossiers").attrib[r"total"])

            if nb_dossiers == 0:
                return self.abort_action(msg=u"Le dossier \'%s\' n'existe pas." % enr_ref_dossier)

            if nb_dossiers > 1:
                return self.abort_action(msg=u"Le nombre de dossiers est incohérent.\n"
                                         u"Merci de contacter l'administrateur Géofoncier.")

            if nb_dossiers == 1:
                # This is the normal case
                dossier_uri = tree.getiterator(tag=r"dossier")[0].find(
                                        r"{http://www.w3.org/2005/Atom}link")
                enr_api_dossier = dossier_uri.attrib[r"href"].split(r"/")[-1][1:]

        else:
            enr_api_dossier = None

        progress_bar.setValue(2)

        # Upload, reset and re-download datasets
        try:
            log = self.upload(enr_api_dossier=enr_api_dossier)
            self.reset()
            self.download(self.url)
        except Exception as e:
            return self.abort_action(msg=e.message)

        self.canvas.zoomToFullExtent()
        self.iface.messageBar().clearWidgets()

        return QMessageBox.information(self, r"Information", u"\r".join(log))

    def download(self, url):

        # Test if permalink is valid
        pattern = r"^(https?:\/\/(\w+[\w\-\.\:\/])+)\?((\&+)?(\w+)\=?([\w\-\.\:\,]+?)?)+(\&+)?$"
        if not re.match(pattern, self.url):
            raise Exception(u"Le permalien n'est pas valide.")

        # Extract params from url
        params = parse_qs(urlparse(self.url).query)

        # Check mandatory parameters
        try:
            context = str(params[r"context"][0])
            center = params[r"centre"][0]
        except:
            raise Exception(u"Les paramètres \'Context\' et \'Centre\' sont obligatoires.")

        auth_contexts = [r"metropole", r"guadeloupe", r"stmartin",
                         r"stbarthelemy", r"guyane", r"reunion", r"mayotte"]

        # Check if context is valid
        if context not in auth_contexts:
            raise Exception(u"La valeur \'%s\' est incorrecte.\n\n"
                            u"\'Context\' doit prentre une des %s valeurs suivantes: "
                            u"%s" % (context, len(auth_contexts), ", ".join(auth_contexts)))

        self.zone = context
        if self.zone in [r"guadeloupe", r"stmartin", r"stbarthelemy"]:
            self.zone = r"antilles"

        # Check if XY are valid
        if not re.match(r"^\-?\d+,\-?\d+$", center):
            raise Exception(u"Les coordonnées XY du centre sont incorrectes.")

        # Extract XY (&centre)
        xcenter = int(center.split(r",")[0])
        ycenter = int(center.split(r",")[1])

        # Compute the bbox
        xmin = xcenter - self.conn.extract_lim / 2
        xmax = xcenter + self.conn.extract_lim / 2
        ymin = ycenter - self.conn.extract_lim / 2
        ymax = ycenter + self.conn.extract_lim / 2

        # Transform coordinates in WGS84
        bbox = tools.reproj(QgsRectangle(xmin, ymin, xmax, ymax), 3857, 4326)

        # Extract RFU (Send the request)
        resp = self.conn.extraction(bbox.xMinimum(), bbox.yMinimum(),
                                    bbox.xMaximum(), bbox.yMaximum())

        if resp.code != 200:
            raise Exception(resp.read())

        tree = EltTree.fromstring(resp.read())

        # Check if error
        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

        # Create the layer: "Masque d'extraction"
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

        self.features_vertex_backed_up = \
            dict((ft[r"fid"], ft) for ft in self.get_features(self.l_vertex))
        self.features_edge_backed_up = \
            dict((ft[r"fid"], ft) for ft in self.get_features(self.l_edge))

        # Get Capabitilies
        resp = self.conn.get_capabilities(self.zone)

        if resp.code != 200:
            raise Exception(resp.read())

        tree = EltTree.fromstring(resp.read())

        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

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
            ft = next(ft for ft in self.l_vertex.getFeatures())
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

        self.downloaded.emit()

        return True

    def reset(self):
        """Remove RFU layers."""

        # Remove RFU layers
        try:
            self.map_layer_registry.removeMapLayers([
                    self.l_vertex.id(), self.l_edge.id(), self.l_bbox.id()])
        except:
            return

        # Reset variable
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

        # Reset ComboBox which contains projections authorized
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

    def upload(self, enr_api_dossier=None):
        """Upload data to Géofoncier REST API.
        On success returns the log messages (Array).

        """

        # Set XML document
        root = EltTree.Element(r"rfu")

        # Add to our XML document datasets which have been changed
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

        # Create a new changeset Id
        changeset_id = self.create_changeset(enr_api_dossier=enr_api_dossier)

        # Add changeset value in our XML document
        root.attrib[r"changeset"] = changeset_id

        # Send data
        edit = self.conn.edit(self.zone, EltTree.tostring(root))
        if edit.code != 200:
            raise Exception(edit.read())

        tree = EltTree.fromstring(edit.read())

        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

        # Returns log info
        msgs_log = []
        for log in tree.iter(r"log"):
            msgs_log.append(u"%s: %s" % (log.attrib[u"type"], log.text))

        # Close the changeset
        self.destroy_changeset(changeset_id)

        # Reset all
        self.edges_added = {}
        self.vertices_added = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}

        return msgs_log

    def create_changeset(self, enr_api_dossier=None):
        """Open a new changeset from Géofoncier API.
        On success, returns the new changeset id.

        """

        opencs = self.conn.open_changeset(self.zone, enr_api_dossier)
        if opencs.code != 200:
            raise Exception(opencs.read())

        tree = EltTree.fromstring(opencs.read())

        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

        treeterator = tree.getiterator(tag=r"changeset")

        # We should get only one changeset
        if len(treeterator) != 1:
            raise Exception(u"Le nombre de \'changeset\' est incohérent.\n"
                            u"Merci de contacter l'administrateur Géofoncier.")

        return treeterator[0].attrib[r"id"]

    def destroy_changeset(self, id):
        """Close a changeset."""

        closecs = self.conn.close_changeset(self.zone, id)

        if closecs.code != 200:
            raise Exception(closecs.read())

        tree = EltTree.fromstring(closecs.read())

        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

        return True

    def abort_action(self, msg=None):

        for layer in self.layers:
            if layer and not layer.isEditable():
                layer.startEditing()

        # Clear message bar
        self.iface.messageBar().clearWidgets()

        if msg:
            return QMessageBox.warning(self, r"Warning", msg)

        return

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
                 (u"Borne, borne à puce, pierre, piquet, clou ou broche"),
                 (u"$id >= 0 AND \"som_nature\" IN ('Borne',"
                  u"'Borne à puce', 'Pierre', 'Piquet', 'Clou ou broche')"),
                 r"#EC0000", 2.2
            ), (
                 (u"Axe cours d'eau, axe fossé, haut de talus, pied de talus"),
                 (u"$id >= 0 AND \"som_nature\" IN ('Axe cours d\'\'eau',"
                  u"'Axe fossé', 'Haut de talus', 'Pied de talus')"),
                 r"#EE8012", 2.2
            ), (
                 (u"Angle de bâtiment, axe de mur, angle de mur, "
                  u"angle de clôture, pylône et toute autre valeur"),
                 (u"$id >= 0 AND \"som_nature\" NOT IN ('Borne',"
                  u"'Borne à puce', 'Pierre', 'Piquet', 'Clou ou broche',"
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
            raise Exception(u"Une erreur est survenue lors du chargement de la couche.")

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
