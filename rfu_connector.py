# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        RFU Connector
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the RFU connector
    * First release: 2015
    * Last release:  2022-05-03
    * Copyright:     (C) 2019,2020,2021, 2022 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QAction, QDockWidget, QMessageBox, QProgressBar, 
                                    QInputDialog, QLineEdit)
from qgis.core import (QgsCoordinateReferenceSystem, QgsFillSymbol, QgsRectangle,
                        QgsVectorLayer, QgsRasterLayer, QgsBrightnessContrastFilter,
                        QgsMarkerSymbol, QgsLineSymbol, QgsRuleBasedRenderer, QgsField,
                        QgsFeature, QgsGeometry, QgsExpression, QgsPalLayerSettings,
                        QgsSingleSymbolRenderer, QgsInvertedPolygonRenderer, QgsMessageLog,
                        QgsEditorWidgetSetup, QgsVectorLayerSimpleLabeling, QgsTextFormat,
                        NULL)
from qgis.gui import QgsMessageBar

import os
import re
import json
import codecs
import xml.etree.ElementTree as EltTree
from urllib.parse import urlparse
from urllib.parse import parse_qs

from . import tools
from .login import GeoFoncierAPILogin
from .config import Configuration
from .global_fnc import *
from .global_vars import *
from .refdoss_cmt_entry import RefDossCmtEntry
from .multidoss_choice import MultiDossChoice


gui_dckwdgt_rfu_connector, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), r"gui/dckwdgt_rfu_connector.ui"))


class RFUDockWidget(QDockWidget, gui_dckwdgt_rfu_connector):

    closed = pyqtSignal()
    downloaded = pyqtSignal()
    uploaded = pyqtSignal()
    rfureset = pyqtSignal()

    def __init__(self, iface, canvas, project, conn=None, parent=None):

        super(RFUDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self.canvas = canvas
        self.project = project
        self.conn = conn
        self.zone = None
        self.precision_class = []
        self.ellips_acronym = []
        self.dflt_ellips_acronym = None
        self.selected_ellips_acronym = None
        self.nature = []
        self.typo_nature_som = []
        self.typo_nature_lim = []
        self.auth_creator = []
        self.tol_same_pt = 0.0
        self.config = Configuration()
        self.url_rfu = self.config.base_url_rfu
        self.url = None
        self.refdoss_cmt = None

        self.l_vertex = None
        self.l_edge = None
        self.layers = [self.l_vertex, self.l_edge]

        # Initialize dicts which contains changed datasets
        self.edges_added = {}
        self.edges_added_ft = {}
        self.vertices_added = {}
        self.vertices_added_ft = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}

        self.downloadPushButton.clicked.connect(self.on_downloaded)
        # self.permalinkLineEdit.returnPressed.connect(self.on_downloaded)
        self.projComboBox.currentIndexChanged.connect(self.set_destination_crs)
        
        # Loads permalinks into the permalink combox
        self.load_permalinks()

        # Create the WMS layer (from Geofoncier)
        self.wms_urlwithparams = 'contextualWMSLegend=0&crs=EPSG:4326&dpiMode=1&featureCount=10&format=image/png&layers=RFU&styles=default&url=' 
        self.wms_urlwithparams += 'https://api.geofoncier.fr' # self.url_rfu
        self.wms_urlwithparams += '/referentielsoge/ogc/wxs/?'
        self.l_wms = QgsRasterLayer(self.wms_urlwithparams, 'Fond de plan RFU WMS', 'wms')
        # Define the contrast filter
        contrast_filter = QgsBrightnessContrastFilter()
        contrast_filter.setContrast(-100)
        # Assign filter to raster pipe
        self.l_wms.pipe().set(contrast_filter)
        
        # Add WMS layer to the registry
        self.project.addMapLayer(self.l_wms, True)
        
        # Apply changes to the WMS layer
        self.l_wms.triggerRepaint()

    def closeEvent(self, event):

        self.closed.emit()

    def on_downloaded(self):

        widget = self.iface.messageBar().createMessage("Géofoncier", "Téléchargement du RFU.")

        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(2)
        widget.layout().addWidget(progress_bar)

        self.iface.messageBar().pushWidget(widget)
        progress_bar.setValue(1)

        # https://pro.geofoncier.fr/index.php?&centre=-196406,5983255&context=metropole
        url = self.permalinkCmb.currentText()

        if not url:
            return self.abort_action(msg="Veuillez renseigner le permalien.")
        self.url = url

        try:
            self.download(self.url)
        except Exception as e:
            return self.abort_action(msg=str(e))
            
        self.save_permalinks(self.url)

        progress_bar.setValue(2)
        self.iface.messageBar().clearWidgets()

        return

    def on_reset(self):

        # Ensure that the action is intentional
        resp = QMessageBox.question(self, reinit_msg[0], reinit_msg[1],
                                    QMessageBox.Yes, QMessageBox.No)
        if resp == QMessageBox.Yes:
            self.reset()
            self.rfureset.emit()

        return

    def on_uploaded(self):

        self.uploaded.emit()

        # Create message
        self.widget = self.iface.messageBar().createMessage("Géofoncier", "Envoi des modifications.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(3)
        self.widget.layout().addWidget(self.progress_bar)
        self.iface.messageBar().pushWidget(self.widget)
        self.progress_bar.setValue(1)
                                
        # Specific dlg to manage the case of several doss with same ref
        self.refdoss_cmt = RefDossCmtEntry()
        self.refdoss_cmt.show()
        # Continue the process after capturing the dic of values
        self.refdoss_cmt.send_refdoss_cmt_vals.connect(self.on_uploaded_withref) 
        
    # Continue the process after dlg validation
    def on_uploaded_withref(self, dic_vals):
        if dic_vals["ok"]:
            enr_ref_dossier = dic_vals["refdoss"]
            self.enr_cmt = dic_vals["cmt"]

            if not enr_ref_dossier:
                return self.abort_action(msg="Merci de renseigner une référence de dossier.")

            # Create correct comment
            if not self.enr_cmt:
                self.enr_cmt = cmt_dft % enr_ref_dossier
            else:
                self.enr_cmt += " - " + cmt_dft % enr_ref_dossier
            
            dossiers = self.conn.dossiersoge_dossiers(self.zone, enr_ref_dossier)
            
            dossiers_read = dossiers.read()
            # DEBUG: Export response as a text file
            # urlresp_to_file(dossiers_read)
            if dossiers.code != 200:
                return self.abort_action(msg=dossiers_read)

            data = json.loads(str(dossiers_read.decode('utf-8')))  

            nb_dossiers = data["count"]

            if nb_dossiers == 0:
                return self.abort_action(msg="Le dossier \'%s\' n'existe pas." % enr_ref_dossier)

            # Case of several same ref_dossier
            # In the case, the difference is made by enr_cab_createur
            if nb_dossiers >= 1:
                doss_infos = []
                for doss in data["results"]:
                    doss_info = []
                    doss_info.append(doss["enr_cab_createur"])
                    doss_info.append(doss["enr_ref_dossier"])
                    # doss_uri = doss.find(r"{http://www.w3.org/2005/Atom}link").attrib[r"href"].split(r"/")[-1][1:]
                    # doss_info.append(doss_uri)
                    
                    # id = enr_api_dossier
                    doss_info.append(doss["id"])
                    doss_info.append(doss["zone"])
                    doss_infos.append(doss_info)
                if len(doss_infos) > 1:
                    self.doss_choice = MultiDossChoice(doss_infos)
                    # Modal window
                    self.doss_choice.setWindowModality(Qt.ApplicationModal)
                    self.doss_choice.show()
                    # Continue the process after capturing the dic of values
                    self.doss_choice.send_refapidoss.connect(self.on_uploaded_proc) 
                else:
                    self.on_uploaded_proc(doss_info[2])
        else:
            self.iface.messageBar().clearWidgets()
            
    # Launch the uploading after receiving the ref_api_doss
    def on_uploaded_proc(self, ref_api_doss): 
        if ref_api_doss != "":
            self.progress_bar.setValue(2)
            # Stop editing mode
            for layer in self.layers:
                if layer.isEditable():
                    self.iface.setActiveLayer(layer)
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
                return self.abort_action(msg="Aucune modification des données n'est détectée.")

            # Upload, reset and re-download datasets
            try:
                log = self.upload(enr_api_dossier=ref_api_doss, commentaire=self.enr_cmt)
                self.reset()
                self.permalinkCmb.setCurrentText(self.url)
                self.download(self.url)
                self.zoom_bbox()
                self.canvas.refresh()
            except Exception as e:
                self.reset()
                self.permalinkCmb.setCurrentText(self.url)
                self.download(self.url)
                self.zoom_bbox()
                self.canvas.refresh()
                return self.abort_action(msg="\n".join(e.args[0]))
            
            self.iface.messageBar().clearWidgets()

            return QMessageBox.information(self, r"Information", "\n".join(log))
        # Case of dlg mutidoss_choice cancelled
        else:
            QMessageBox.information(self, multi_doss_canceled_msg[0], multi_doss_canceled_msg[1])
            self.iface.messageBar().clearWidgets()

    def download(self, url):

        # Test if permalink is valid
        pattern = r"^(https?:\/\/(\w+[\w\-\.\:\/])+)\?((\&+)?(\w+)\=?([\w\-\.\:\,]+?)?)+(\&+)?$"
        if not re.match(pattern, self.url):
            raise Exception("Le permalien n'est pas valide.")

        # Extract params from url
        params = parse_qs(urlparse(self.url).query)

        # Check mandatory parameters
        try:
            context = str(params[r"context"][0])
            center = params[r"centre"][0]
        except:
            raise Exception("Les paramètres \'Context\' et \'Centre\' sont obligatoires.")

        auth_contexts = [r"metropole", r"guadeloupe", r"stmartin",
                         r"stbarthelemy", r"guyane", r"reunion", r"mayotte", r"martinique"]

        # Check scale parameter
        try:
            scale = int(params[r"echelle"][0])
        except:
            raise Exception("Le paramètre \'Echelle\' est obligatoire.")
        else:
            if scale > scale_limit:
                raise Exception(wrong_scale_txt.format(str(scale_limit)))
            
        # Check if context is valid
        if context not in auth_contexts:
            raise Exception("La valeur \'%s\' est incorrecte.\n\n"
                            "\'Context\' doit prentre une des %s valeurs suivantes: "
                            "%s" % (context, len(auth_contexts), ", ".join(auth_contexts)))

        self.zone = context
        if self.zone in [r"guadeloupe", r"stmartin", r"stbarthelemy", r"martinique"]:
            self.zone = r"antilles"

        # Check if XY are valid
        if not re.match(r"^\-?\d+,\-?\d+$", center):
            raise Exception("Les coordonnées XY du centre sont incorrectes.")

        # Extract XY (&centre)
        xcenter = int(center.split(r",")[0])
        ycenter = int(center.split(r",")[1])

        # Compute the bbox
        xmin = xcenter - self.conn.extract_lim / 2
        xmax = xcenter + self.conn.extract_lim / 2
        ymin = ycenter - self.conn.extract_lim / 2
        ymax = ycenter + self.conn.extract_lim / 2
        
        # Transform coordinates in WGS84
        bbox = tools.reproj(QgsRectangle(xmin, ymin, xmax, ymax), 3857, 4326, self.project)

        # Extract RFU (Send the request)
        resp = self.conn.extraction(bbox.xMinimum(), bbox.yMinimum(),
                                    bbox.xMaximum(), bbox.yMaximum())

        resp_read = resp.read()
        
        # DEBUG: Export response as a text file
        # urlresp_to_file(resp_read)
        
        if resp.code != 200:
            raise Exception(resp_read)
        tree = EltTree.fromstring(resp_read)
        # Check if error
        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

        # Create the layer: "Masque d'extraction"
        self.l_bbox = QgsVectorLayer(r"Polygon?crs=epsg:4326&index=yes",
                                     "Zone de travail", r"memory")

        p_bbox = self.l_bbox.dataProvider()

        simple_symbol = QgsFillSymbol.createSimple({
                                r"color": r"116,97,87,255",
                                r"style": r"b_diagonal",
                                r"outline_style": r"no"})

        renderer_bbox = QgsInvertedPolygonRenderer(QgsSingleSymbolRenderer(simple_symbol))

        self.l_bbox.setRenderer(renderer_bbox)

        self.ft_bbox = QgsFeature()
        self.limit_area = QgsRectangle(bbox.xMinimum(), bbox.yMinimum(),
                                       bbox.xMaximum(), bbox.yMaximum())
        self.ft_bbox.setGeometry(QgsGeometry.fromRect(self.limit_area))
        p_bbox.addFeatures([self.ft_bbox])

        self.l_bbox.updateFields()
        self.l_bbox.updateExtents()
        
        # Create layers..
        self.layers = self.extract_layers(tree)
        self.l_vertex = self.layers[0]
        self.l_edge = self.layers[1]

        # Add layer to the registry
        self.project.addMapLayers([self.l_vertex, self.l_edge, self.l_bbox])

        # Set extent
        # self.canvas.setExtent(QgsRectangle(bbox.xMinimum(), bbox.yMinimum(),
                                           # bbox.xMaximum(), bbox.yMaximum()))
        
        self.features_vertex_backed_up = \
            dict((ft[r"fid"], ft) for ft in self.get_features(self.l_vertex))
        self.features_edge_backed_up = \
            dict((ft[r"fid"], ft) for ft in self.get_features(self.l_edge))

        # Get Capabitilies
        resp = self.conn.get_capabilities(self.zone)
        resp_read = resp.read()
        
        # DEBUG
        # urlresp_to_file(resp_read)

        if resp.code != 200:
            raise Exception(resp_read)

        tree = EltTree.fromstring(resp_read)
        
        # Find tolerance to determine if 2 points are equals
        for entry in tree.findall(r"./tolerance"):
            self.tol_same_pt = float(entry.text)
        
        err = tree.find(r"./erreur")
        if err:
            raise Exception(err.text)

        for entry in tree.findall(r"./classe_rattachement/classe"):
            t = (entry.attrib[r"som_precision_rattachement"], entry.text)
            self.precision_class.append(t)

        for entry in tree.findall(r"./representation_plane_sommet_autorise/representation_plane_sommet"):
            t = (entry.attrib[r"som_representation_plane"], entry.attrib[r"epsg_crs_id"], entry.text)
            self.ellips_acronym.append(t)
            
        # Added v2.1 <<
        for entry in tree.findall(r"./typologie_nature_sommet/nature"):
            self.typo_nature_som.append(entry.text)           
        
        for entry in tree.findall(r"./nature_sommet_conseille/nature"):
            self.nature.append(entry.text)
            
        for entry in tree.findall(r"./typologie_nature_limite/nature"):
            self.typo_nature_lim.append(entry.text)
        # >>

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
            
            if not self.dflt_ellips_acronym and i==0:
                self.project_crs = int(e[1])

            if self.dflt_ellips_acronym == e[0]:

                # Check projection in combobox
                self.projComboBox.setCurrentIndex(i)

                # Then change the CRS in canvas
                epsg_str = "EPSG:" + str(int(e[1]))
                crs = QgsCoordinateReferenceSystem(epsg_str)
                self.project.setCrs(crs)
                self.project_crs = int(e[1])
        
        # Calculate bbox in the project CRS (used for the scale limitation of the canvas)
        self.bbox_crsproject = tools.reproj(QgsRectangle(xmin, ymin, xmax, ymax), 3857, self.project_crs, self.project)
        
        # Zoom to bbox extents
        self.zoom_bbox()       
        self.canvas.refresh()
        
        # Modified in v2.1 <<
        # Add the list of possible values to the field som_nature
        map_predefined_vals_to_fld(self.l_vertex, "som_typologie_nature", self.typo_nature_som) 
        # Add the list of possible values to the field som_precision_rattachement
        map_predefined_vals_to_fld(self.l_vertex, "som_precision_rattachement", self.precision_class, 0, 1)
        # Add the list of possible values to the field som_precision_rattachement
        map_predefined_vals_to_fld(self.l_vertex, "som_representation_plane", self.ellips_acronym, 0, 2)       
        # Add the list of possible values to the field lim_typologie_nature
        map_predefined_vals_to_fld(self.l_edge, "lim_typologie_nature", self.typo_nature_lim)
        # Add the list of possible values to the field som_delimitation_publique
        false_true_lst = [('False', 'Faux'), ('True', 'Vrai')]
        map_predefined_vals_to_fld(self.l_vertex, "som_delimitation_publique", false_true_lst, 0, 1)
        # Add the list of possible values to the field lim_delimitation_publique
        map_predefined_vals_to_fld(self.l_edge, "lim_delimitation_publique", false_true_lst, 0, 1)
        # >>
        
        # Then, start editing mode..
        for idx, layer in enumerate(self.layers):
            if not layer.isEditable():
                layer.startEditing()
            if idx == 0:
                self.iface.setActiveLayer(layer)

        self.projComboBox.setDisabled(False)

        self.permalinkCmb.setDisabled(True)
        self.downloadPushButton.setDisabled(True)
        self.resetPushButton.setDisabled(False)
        self.uploadPushButton.setDisabled(False)

        self.downloadPushButton.clicked.disconnect(self.on_downloaded)
        # self.permalinkLineEdit.returnPressed.disconnect(self.on_downloaded)
        self.resetPushButton.clicked.connect(self.on_reset)
        self.uploadPushButton.clicked.connect(self.on_uploaded)
        
        # Activate the scale limitation for the canvas
        self.canvas.scaleChanged.connect(self.limit_cvs_scale)

        self.downloaded.emit()

        return True

    def reset(self):
        """Remove RFU layers."""
        
        # Save (virtually) the changes in the layers
        # (to avoid alert messages when removing the layers)
        for layer in self.layers :
            if isinstance(layer, QgsVectorLayer):
                if layer.isEditable():
                    self.iface.setActiveLayer(layer)
                    layer.commitChanges()
        
        # Remove RFU layers
        try:
            self.project.removeMapLayers([
                    self.l_vertex.id(), self.l_edge.id(), self.l_bbox.id()])
        except:
            return
            
        # Remove eliminated lines layer
        if self.project.mapLayersByName(elimedge_lname):
            el_lyr = self.project.mapLayersByName(elimedge_lname)[0]
            self.iface.setActiveLayer(el_lyr)
            el_lyr.commitChanges()
            self.project.removeMapLayers([el_lyr.id()])
        
        # Reset variable
        self.precision_class = []
        self.ellips_acronym = []
        self.dflt_ellips_acronym = None
        self.nature = []
        self.typo_nature_lim = []
        self.typo_nature_som = []
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
        self.tol_same_pt = 0.0

        # Reset ComboBox which contains projections authorized
        self.projComboBox.clear()
        self.projComboBox.setDisabled(True)

        # Loads permalinks into the permalink combox
        self.load_permalinks()
        self.permalinkCmb.setDisabled(False)
        # self.permalinkLineEdit.returnPressed.connect(self.on_downloaded)

        self.downloadPushButton.setDisabled(False)
        self.downloadPushButton.clicked.connect(self.on_downloaded)

        self.resetPushButton.setDisabled(True)
        self.resetPushButton.clicked.disconnect(self.on_reset)

        self.uploadPushButton.setDisabled(True)
        self.uploadPushButton.clicked.disconnect(self.on_uploaded)

        return True

    def upload(self, enr_api_dossier=None, commentaire=None):
        """Upload data to Géofoncier REST API.
        On success returns the log messages (Array).

        """

        # Set XML document
        root = EltTree.Element(r"rfu")
        first_vtx_kept = True
        first_edge_kept = True
        # Add to our XML document datasets which have been changed
        if self.vertices_added:
            for fid in self.vertices_added:
                # Check if vertex is out of the bbox
                to_export = check_vtx_outofbbox(self.vertices_added_ft[fid], self.ft_bbox)
                if to_export:
                    tools.xml_subelt_creator(root, "sommet",
                                             data=self.vertices_added[fid],
                                             action=r"create")
                # If vertex is out of the bbox
                else:
                    # Create a new layer to store the vertices non exported
                    if first_vtx_kept:
                        if layer_exists(vtx_outofbbox_lname, self.project):
                            vtx_outofbbox_lyr = self.project.mapLayersByName(vtx_outofbbox_lname)[0]
                        else:
                            vtx_outofbbox_lyr = create_vtx_outofbbox_lyr()
                    # Add the vertex to this layer
                    if not vtx_outofbbox_lyr.isEditable():
                        vtx_outofbbox_lyr.startEditing()
                    vtx_outofbbox_lyr.addFeature(self.vertices_added_ft[fid])
                    first_vtx_kept = False
        if self.edges_added:
            for fid in self.edges_added:
                # Check if edge is out of the bbox
                to_export = check_edge_outofbbox(self.edges_added_ft[fid], self.ft_bbox)
                if to_export:
                    tools.xml_subelt_creator(root, "limite",
                                             data=self.edges_added[fid],
                                             action=r"create")
                # If edge is out of the bbox
                else:
                    # Create a new layer to store the edges non exported
                    if first_edge_kept:
                        if layer_exists(edge_outofbbox_lname, self.project):
                            edge_outofbbox_lyr = self.project.mapLayersByName(edge_outofbbox_lname)[0]
                        else:
                            edge_outofbbox_lyr = create_edge_outofbbox_lyr()
                    # Add the edge to this layer
                    if not edge_outofbbox_lyr.isEditable():
                        edge_outofbbox_lyr.startEditing()
                    edge_outofbbox_lyr.addFeature(self.edges_added_ft[fid])
                    first_edge_kept = False
        if self.vertices_removed:
            for fid in self.vertices_removed:
                tools.xml_subelt_creator(root, "sommet",
                                         data=self.vertices_removed[fid],
                                         action=r"delete")
        if self.edges_removed:
            for fid in self.edges_removed:
                tools.xml_subelt_creator(root, "limite",
                                         data=self.edges_removed[fid],
                                         action=r"delete")
        if self.vertices_modified:
            for fid in self.vertices_modified:
                tools.xml_subelt_creator(root, "sommet",
                                         data=self.vertices_modified[fid],
                                         action=r"update")
        if self.edges_modified:
            for fid in self.edges_modified:
                tools.xml_subelt_creator(root, "limite",
                                         data=self.edges_modified[fid],
                                         action=r"update")
        # Create a new changeset Id
        changeset_id = self.create_changeset(enr_api_dossier=enr_api_dossier, commentaire=commentaire)
        # Add changeset value in our XML document
        root.attrib[r"changeset"] = changeset_id
        
        # Send data
        edit = self.conn.edit(self.zone, EltTree.tostring(root))
        if edit.code != 200:
            edit_read = edit.read()
            # DEBUG
            # urlresp_to_file(edit_read)
            err_tree = EltTree.fromstring(edit_read)
            msgs_log = []
            for log in err_tree.iter(r"log"):
                msgs_log.append("%s: %s" % (log.attrib["type"], log.text))
            raise Exception(msgs_log)
        tree = EltTree.fromstring(edit.read())
        err = tree.find(r"./erreur")
        if err:
            debug_msg('DEBUG', "erreur: %s" , (str(err)))
            err_tree = EltTree.fromstring(err)
            msgs_log = []
            for log in err_tree.iter(r"log"):
                msgs_log.append("%s: %s" % (log.attrib["type"], log.text))
            raise Exception(msgs_log)

        # Returns log info
        msgs_log = []
        for log in tree.iter(r"log"):
            msgs_log.append("%s: %s" % (log.attrib["type"], log.text))

        # Close the changeset
        self.destroy_changeset(changeset_id)

        # Reset all
        self.edges_added = {}
        self.edges_added_ft = {}
        self.vertices_added = {}
        self.vertices_added_ft = {}
        self.edges_removed = {}
        self.vertices_removed = {}
        self.edges_modified = {}
        self.vertices_modified = {}
        
        # Alert message if elements out of bbox
        msg_outbbox = ""
        if not first_vtx_kept:
            msg_outbbox = msg_outbbox_vtx.format(vtx_outofbbox_lname)
        if not first_edge_kept:
            if msg_outbbox != "":
                msg_outbbox += "<br>"
            msg_outbbox += msg_outbbox_edge.format(edge_outofbbox_lname)
        if msg_outbbox != "":
            self.canvas.refresh()
            m_box = mbox_w_params(tl_atn, txt_msg_outbbox, msg_outbbox)
            m_box.exec_()
        return msgs_log

    def create_changeset(self, enr_api_dossier=None, commentaire=None):
        """Open a new changeset from Géofoncier API.
        On success, returns the new changeset id.

        """

        opencs = self.conn.open_changeset(self.zone, enr_api_dossier=enr_api_dossier, commentaire=commentaire)
        if opencs.code != 200:
            raise Exception(opencs.read())

        tree = EltTree.fromstring(opencs.read())

        err = tree.find(r"./log")
        if err:
            raise Exception(err.text)

        # treeterator = list(tree.getiterator(tag=r"changeset"))
        # Python 3.9 -> getiterator deprecated
        treeterator = list(tree.iter(tag=r"changeset"))

        # We should get only one changeset
        if len(treeterator) != 1:
            raise Exception("Le nombre de \'changeset\' est incohérent.\n"
                            "Merci de contacter l'administrateur Géofoncier.")

        return treeterator[0].attrib[r"id"]

    def destroy_changeset(self, id):
        """Close a changeset."""

        closecs = self.conn.close_changeset(self.zone, id)

        if closecs.code != 200:
            raise Exception(closecs.read())

        tree = EltTree.fromstring(closecs.read())

        err = tree.find(r"./log")
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
            return QMessageBox.warning(self, r"Attention", msg)

        return

    def extract_layers(self, tree):
        """Return a list of RFU layers."""
        
        # Create vector layers..
        l_vertex = QgsVectorLayer(r"Point?crs=epsg:4326&index=yes",
                                  "Sommet RFU", r"memory")
        l_edge = QgsVectorLayer(r"LineString?crs=epsg:4326&index=yes",
                                "Limite RFU", r"memory")

        p_vertex = l_vertex.dataProvider()
        p_edge = l_edge.dataProvider()

        # Define default style renderer..
        renderer_vertex = QgsRuleBasedRenderer(QgsMarkerSymbol())
        vertex_root_rule = renderer_vertex.rootRule()
        
        # Modified in v2.1 (som_nature replaced by som_typologie_nature) >>
        vertex_rules = (
            (
                 ("Borne, borne à puce, pierre, piquet, clou ou broche"),
                 ("$id >= 0 AND \"som_typologie_nature\" IN ('Borne',"
                  "'Borne à puce', 'Pierre', 'Piquet', 'Clou ou broche')"),
                 r"#EC0000", 2.2
            ), (
                 ("Axe cours d'eau, axe fossé, haut de talus, pied de talus"),
                 ("$id >= 0 AND \"som_typologie_nature\" IN ('Axe cours d\'\'eau',"
                  "'Axe fossé', 'Haut de talus', 'Pied de talus')"),
                 r"#EE8012", 2.2
            ), (
                 ("Angle de bâtiment, axe de mur, angle de mur, "
                  "angle de clôture, pylône et toute autre valeur"),
                 ("$id >= 0 AND \"som_typologie_nature\" NOT IN ('Borne',"
                  "'Borne à puce', 'Pierre', 'Piquet', 'Clou ou broche',"
                  "'Axe cours d\'\'eau', 'Axe fossé', 'Haut de talus',"
                  "'Pied de talus')"),
                 r"#9784EC", 2.2
            ), (
                "Temporaire", r"$id < 0", "cyan", 2.4
            ),
               (
                "Point nouveau à traiter car proche d'un existant", r"point_rfu_proche is not null", "#bcff03", 3
            ))
            
        # >>

        for label, expression, color, size in vertex_rules:
            rule = vertex_root_rule.children()[0].clone()
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().setColor(QColor(color))
            rule.symbol().setSize(size)
            vertex_root_rule.appendChild(rule)

        vertex_root_rule.removeChildAt(0)
        l_vertex.setRenderer(renderer_vertex)

        renderer_edge = QgsRuleBasedRenderer(QgsLineSymbol())
        edge_root_rule = renderer_edge.rootRule()
        
        # Modified in v2.1 (lim_typologie_nature added) <<
        edge_rules = (  
                        (
                            "Limite privée", 
                            "$id >= 0 AND \"lim_typologie_nature\" = '" + lim_typo_nat_vals[0] + "'",
                            "#0A0AFF", 
                            0.5
                        ),
                        (
                            "Limite naturelle", 
                            "$id >= 0 AND \"lim_typologie_nature\" = '" + lim_typo_nat_vals[1] + "'",
                            "#aa876d", 
                            0.5
                        ),
                        (
                            "Temporaire", 
                            "$id < 0", 
                            "cyan", 
                            1
                        )
                    )
                      
        # >>

        for label, expression, color, width in edge_rules:
            rule = edge_root_rule.children()[0].clone()
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            rule.symbol().setColor(QColor(color))
            rule.symbol().setWidth(width)
            edge_root_rule.appendChild(rule)

        edge_root_rule.removeChildAt(0)
        l_edge.setRenderer(renderer_edge)

        # Add fields..
        p_vertex.addAttributes(vtx_atts)

        p_edge.addAttributes(edge_atts)

        # Add features from xml tree..
        # ..to vertex layer..
        fts_vertex = []
        for e in tree.findall(r"sommet"):

            ft_vertex = QgsFeature()
            ft_vertex.setGeometry(QgsGeometry.fromWkt(e.attrib[r"geometrie"]))
            _id_noeud = int(e.attrib[r"id_noeud"])
            _version = int(e.attrib[r"version"])
            som_ge_createur = str(e.find(r"./som_ge_createur").text)
            som_nature = str(e.find(r"./som_nature").text)
            som_prec_rattcht = int(e.find(r"./som_precision_rattachement").text)
            som_coord_est = float(e.find(r"./som_coord_est").text)
            som_coord_nord = float(e.find(r"./som_coord_nord").text)
            som_repres_plane = str(e.find(r"./som_representation_plane").text)
            som_tolerance = float(e.find(r"./som_tolerance").text)
            # Field used to store the attestation_qualite value 
            # when modifying a vertex ("false" or "true")
            attestation_qualite = "false"
                            
            som_delim_pub = str(e.find(r"./som_delimitation_publique").text)
            som_typo_nature = str(e.find(r"./som_typologie_nature").text)
            
            ft_vertex.setAttributes([
                        _id_noeud,
                        _version,
                        som_ge_createur,
                        som_delim_pub,
                        som_typo_nature,
                        som_nature,
                        som_prec_rattcht,
                        som_coord_est,
                        som_coord_nord,
                        som_repres_plane,
                        som_tolerance,
                        attestation_qualite,
                        NULL
                        ])

            fts_vertex.append(ft_vertex)

        # ..to edge layer..
        fts_edge = []
        for e in tree.findall(r"limite"):

            ft_edge = QgsFeature()
            ft_edge.setGeometry(QgsGeometry.fromWkt(e.attrib[r"geometrie"]))
            _id_arc = int(e.attrib[r"id_arc"])
            _version = int(e.attrib[r"version"])
            lim_ge_createur = str(e.find(r"./lim_ge_createur").text)
            
            lim_typo_nature = str(e.find(r"./lim_typologie_nature").text)
            lim_delim_pub = str(e.find(r"./lim_delimitation_publique").text)
            
            ft_edge.setAttributes([
                        _id_arc,
                        _version,
                        lim_ge_createur,
                        lim_delim_pub,
                        lim_typo_nature
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
            raise Exception("Une erreur est survenue lors du chargement de la couche.")

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
                self.vertices_added_ft[ft.id()] = ft

            if layer_id == self.l_edge.id():
                self.edges_added[ft.id()] = attrib
                self.edges_added_ft[ft.id()] = ft

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

        epsg_str = "EPSG:" + str(epsg)
        crs = QgsCoordinateReferenceSystem(epsg_str)
        self.project.setCrs(crs)       
        
    # Stop zoom when the scale limit is exceeded
    def limit_cvs_scale(self):
        if self.canvas.scale() > cvs_scale_limit:
            self.disconn_scale_limit()
            self.zoom_bbox()
            self.canvas.zoomScale(cvs_scale_limit)
            self.canvas.scaleChanged.connect(self.limit_cvs_scale)

    def zoom_bbox(self):
        self.canvas.setExtent(QgsRectangle(
                                            self.bbox_crsproject.xMinimum(),
                                            self.bbox_crsproject.yMinimum(),
                                            self.bbox_crsproject.xMaximum(),
                                            self.bbox_crsproject.yMaximum()
                                           )
                              )
    
    def disconn_scale_limit(self):
        self.canvas.scaleChanged.disconnect(self.limit_cvs_scale)
        
    def conn_scale_limit(self):
        self.canvas.scaleChanged.connect(self.limit_cvs_scale)
        
    # Loads permalinks from the json file into the combobox
    def load_permalinks(self):
        try:
            self.json_path = os.path.join(os.path.dirname(__file__), r"permalinks.json")
        except IOError as error:
            raise error
        with codecs.open(self.json_path, encoding='utf-8', mode='r') as json_file:
            json_permalinks = json.load(json_file)
            self.permalinks = json_permalinks[r"permalinks"]
            current_permalink_idx = json_permalinks[r"current_permalink_idx"]
        if len(self.permalinks) > 0:
            self.permalinkCmb.clear()
            for idx, permalink in enumerate(self.permalinks):
                self.permalinkCmb.addItem(permalink)
            self.permalinkCmb.setCurrentIndex(current_permalink_idx)
            # self.permalinkCmb.lineEdit().selectAll()
            
    # Save permalinks in the json file (limited to 5 permalinks)
    def save_permalinks(self, permalink):
        # Update the json file
        json_permalinks = {}
        if permalink not in self.permalinks:
            # Update the permalinks list
            if len(self.permalinks) == 5:
                del self.permalinks[0]
            self.permalinks.append(permalink)
            json_permalinks["current_permalink_idx"] = len(self.permalinks) - 1
        else:
            json_permalinks["current_permalink_idx"] = self.permalinkCmb.currentIndex()
        json_permalinks["permalinks"] = self.permalinks
        
        with codecs.open(self.json_path, encoding='utf-8', mode='w') as json_file:
                json_file.write(json.dumps(json_permalinks, indent=4, separators=(',', ': '), ensure_ascii=False))
                
        
    

            