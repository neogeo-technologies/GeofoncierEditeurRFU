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
# from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import QVariant
# from PyQt4.QtCore import QDateTime
# from PyQt4.QtCore import QDate
from PyQt4.QtGui import QColor
from PyQt4.QtGui import QDockWidget
from PyQt4.QtGui import QMessageBox
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


import tools
from login import GeoFoncierAPILogin


gui_dckwdgt_rfu_connector, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), r"gui/dckwdgt_rfu_connector.ui"))


class RFUDockWidget(QDockWidget, gui_dckwdgt_rfu_connector):

    def __init__(self, map_layer_registry, conn=None, parent=None):

        super(RFUDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.map_layer_registry = map_layer_registry
        self.conn = conn
        self.zone = None
        self.precision_class = []
        self.ellips_acronym = []
        self.dflt_ellips_acronym = None
        self.nature = []
        self.auth_creator = []

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

    def open_connection(self):
        """Call GeoFoncierAPILogin() ie. the `Sign In` DialogBox.
        If accepted -> return a new APIClient() obj.

        """
        dlg_login = GeoFoncierAPILogin()
        dlg_login.show()

        # Test if failed..
        if not dlg_login.exec_():
            return None

        # Then..
        return dlg_login.conn

    def on_downloaded(self):
        self.download()

    def download(self):

        # Connect to API if none..
        if not self.conn:
            self.conn = self.open_connection()
        if not self.conn:
            return None

        # https://pro.geofoncier.fr/index.php?
        #    &echelle=18056
        #    &centre=-196406,5983255
        #    &context=metropole
        #    &layers=RFU_FXX,PCI_VECTEUR

        url = self.permalinkLineEdit.text()

        if not url:
            msg = u"Veuillez renseigner le permalien."
            return QMessageBox.warning(self, r"Warning", msg)

        # Test if permalink is valid (&centre and &context are mandatory)..
        pattern = r"^(https?:\/\/(\w+[\-\.\/\w])+)(((\?|\&)(context|centre|\w+))\=?[\w\,\-\.]+?)+&?$"
        if not re.match(pattern, url):
            msg = u"Le permalien n'est pas valide."
            return QMessageBox.warning(self, r"Warning", msg)

        # Extract params from url..
        params = parse_qs(urlparse(url).query)

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
            # Catch the error specified by the API..
            e = tools.tree_parser(resp.read(), xpath=r"./erreur")
            if e.text:
                msg = e.text
            else:
                # Or error returned by the server (all other cases)..
                msg = str(resp)
            # Then display the error in a message box..
            return QMessageBox.warning(self, r"Warning", msg)

        xml = resp.read()

        # isvalid = self.extraction_isvalid(xml)
        # if isvalid is False:
        #     msg = u"L'extraction RFU n'est pas valide."
        #     return QMessageBox.warning(self, r"Warning", msg)

        # Create layers..
        self.layers = self.extract_layers(xml)
        self.l_vertex = self.layers[0]
        self.l_edge = self.layers[1]

        # Then add layers to the map..
        self.map_layer_registry.addMapLayers(self.layers)

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
            # Catch the error specified by the API..
            e = tools.tree_parser(resp.read(), xpath=r"./erreur")
            if e.text:
                msg = e.text
            else:
                # Or error returned by the server (all other cases)..
                msg = str(resp)
            # Then display the error in a message box..
            return QMessageBox.warning(self, r"Warning", msg)

        tree = EltTree.fromstring(resp.read())

        for entry in tree.findall(r"./classe_rattachement/classe"):
            t = (entry.attrib[r"som_precision_rattachement"], entry.text)
            self.precision_class.append(t)

        for entry in tree.findall(r"./representation_plane_sommet_autorise/representation_plane_sommet"):
            t = (entry.attrib[r"som_representation_plane"], entry.text)
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
            self.projComboBox.addItem(e[1])
            if not self.dflt_ellips_acronym:
                continue
            if self.dflt_ellips_acronym == e[0]:
                self.projComboBox.setCurrentIndex(i)

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

        self.reset()

    def reset(self):
        """Remove RFU layers."""

        # Remove RFU layers..
        try:
            self.map_layer_registry.removeMapLayers([l.id() for l in self.layers])
        except:
            pass

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

    def on_uploaded(self):

        # Stop editing mode..
        for layer in self.layers:
            if layer.isEditable():
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
            return None

        # Ensure that the action is intentional..
        msg = (u"Vous êtes sur le point de soumettre "
               u"les modifications au serveur GéoFoncier. "
               u"Souhaitez-vous poursuivre cette action ?")

        resp = QMessageBox.question(self, r"Question", msg,
                                    QMessageBox.Yes, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return False

        self.upload()
        self.reset()
        self.download()

        # self.permalinkLineEdit.setDisabled(True)
        # self.downloadPushButton.setDisabled(True)
        # self.resetPushButton.setDisabled(False)
        # self.uploadPushButton.setDisabled(False)

        # self.downloadPushButton.clicked.disconnect(self.on_downloaded)
        # self.permalinkLineEdit.returnPressed.disconnect(self.on_downloaded)
        # self.resetPushButton.clicked.connect(self.on_reset)
        # self.uploadPushButton.clicked.connect(self.on_uploaded)

        QMessageBox.information(
                    self, u"Information",
                    u"Les modifications du RFU sont enregistrées.")

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
                                         data=self.vertices_removed[fid],
                                         action=r"update")

        if self.edges_modified:
            for fid in self.edges_modified:
                tools.xml_subelt_creator(root, u"limite",
                                         data=self.edges_modified[fid],
                                         action=r"update")

        # Open a new Changeset..
        opencs = self.conn.open_changeset(self.zone)
        if opencs.code != 200:
            tree = EltTree.fromstring(opencs.read())
            elt_err = tree.find(r"./erreur")
            if elt_err.text:
                msg = elt_err.text
            else:
              msg = str(resp)
            return QtGui.QMessageBox.warning(self, r"Warning", msg)

        treeterator = EltTree.fromstring(opencs.read()).getiterator(tag=r"changeset")
        if len(treeterator) != 1:
            msg = u"Une erreur est survenue."
            return QMessageBox.warning(self, r"Warning", msg)

        changeset_id = treeterator[0].attrib[r"id"]
        root.attrib[r"changeset"] = changeset_id

        # Send data..
        edit = self.conn.edit(self.zone, EltTree.tostring(root))
        if edit.code != 200:
            tree = EltTree.fromstring(edit.read())
            elt_err = tree.find(r"./erreur")
            if elt_err.text:
                msg = elt_err.text
            else:
              msg = str(resp)
            return QtGui.QMessageBox.warning(self, r"Warning", msg)

        # Close the changeset..
        close_changeset = self.conn.close_changeset(self.zone, changeset_id)
        if close_changeset.code != 200:
            tree = EltTree.fromstring(close_changeset.read())
            elt_err = tree.find(r"./erreur")
            if elt_err.text:
                msg = elt_err.text
            else:
              msg = str(resp)
            return QtGui.QMessageBox.warning(self, r"Warning", msg)

        # Reset all..
        self.edges_added = {}
        self.vertices_added = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}

    def extract_layers(self, xml):
        """Return a list of RFU layers."""

        tree = EltTree.fromstring(xml)

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
