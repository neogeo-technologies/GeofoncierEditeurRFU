# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Import CSV RFU
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the possibility to import a CSV file
    *                (structured for RFU).
    * First release: 2018-06-01
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox, QFileDialog
from qgis.core import QgsPointXY, QgsWkbTypes, QgsFeature, QgsGeometry, NULL

import os
import csv
import math

from .global_vars import *
from .global_fnc import *


class ImportCsvRfu:
    
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
        self.cc = selected_ellips_acronym
        self.typo_nature_som = typo_nature_som
        self.typo_nature_lim = typo_nature_lim
        self.tol_spt = tol_spt
        self.edge = None
        
    def import_file(self) :
        existingPts = []
        self.original_l_vtx = self.l_vertex
        self.original_l_edge = self.l_edge
        csv_rfu_file = QFileDialog.getOpenFileName (
                None,
                tl_csv_choice,
                os.path.expanduser("~"),
                "CSV (*.csv)"
                )[0]
        if not csv_rfu_file:
            QMessageBox.information(self.iface.mainWindow(), tl_imp_canc, txt_csvimp_canc)
            return None
        else:
            csv_som = []
            csv_nw_pt = {}
            csv_lim = []
            nw_edge = []
            ge_createur = self.user
            # Extraction of the CSV lines
            csv_rfu = csv.reader(open(csv_rfu_file, "r", encoding='iso-8859-1'), delimiter = ";")
            for csv_row in csv_rfu:
                # Find creator
                if csv_row[0] == "Géomètre" and csv_row[1] != '':
                    ge_createur = csv_row[1][:5]
                # Creation of a list of sommets
                if csv_row[0] == "Sommet":
                    if csv_row[2] != '' and csv_row[3] != '':
                        csv_som.append(csv_row[1:])
                        csv_nw_pt[csv_row[2]] = QgsPointXY(float(csv_row[3]), float(csv_row[4]))
                # Creation of a list of limites (double numbers)
                elif csv_row[0][:6] == "Limite" and csv_row[0] != '':
                    # Check if the type of limite is correct, 
                    # otherwise, apply the default type
                    if csv_row[0] in self.typo_nature_lim:
                        lim_typo_nat = csv_row[0]
                    else:
                        lim_typo_nat = lim_typo_nat_vals[0]
                    if csv_row[1].lower() == 'oui':
                        lim_delim_pub = 'True'
                    else:
                        lim_delim_pub = 'False'
                    lim_pt = []
                    for pt_num in csv_row[2:]:
                        if pt_num != '':
                            lim_pt.append(pt_num)
                    if lim_pt != []:
                        # Creation of the list of edges (2 points + attributes)
                        for idx, nw_num in enumerate(lim_pt):
                            if idx > 0:
                                nw_edge.append([    csv_nw_pt[lim_pt[idx-1]], 
                                                    csv_nw_pt[nw_num],
                                                    lim_delim_pub,
                                                    lim_typo_nat
                                                ])

            # Creation of the vertices
            elim_pts = []
            self.iface.setActiveLayer(self.l_edge)
            self.iface.setActiveLayer(self.l_vertex)
            # Transformations to obtain the WGS84 or the CC coordinates
            coords_trf_wgs, coords_trf_cc = crs_trans_params(self.canvas, self.project)
            for nw_som in csv_som:
                nw_pt = csv_nw_pt[nw_som[1]]
                if nw_som[0].lower() == 'oui':
                    som_delim_pub = 'True'
                else:
                    som_delim_pub = 'False'
                idx_prec = nw_som[4]
                pt_type = nw_som[5]
                # Check if the type of sommet is correct, 
                # otherwise, apply the default type
                if pt_type not in self.typo_nature_som:
                    pt_type = dft_som_typo_nat 
                pt_type_cmt = nw_som[5]
                if nw_som[6] != '':
                    pt_type_cmt = nw_som[6]
                nw_pt_wgs = coords_trf_wgs.transform(nw_pt)
                # Check if the new vertex is in the tolerance of an existing vertex in the RFU
                to_create = True
                id_ptintol = NULL
                for vtx_feat in self.original_l_vtx.getFeatures() :
                    vtx_feat_g = vtx_feat.geometry()
                    vtx_tol = vtx_feat['som_tolerance']
                    if vtx_feat_g.type() == QgsWkbTypes.PointGeometry :
                        vtx_feat_pt = vtx_feat_g.asPoint()
                        vtx_feat_pt_cc = coords_trf_cc.transform(vtx_feat_pt)
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
                                    # Round the pt coordinates to get the same accuracy 
                                    # as in the csv file
                                    rp_pt = round_pt_2_cm(vtx_feat_pt_cc)
                                    elim_dbpt.append(rp_pt)
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
                                # Round the pt coordinates to get the same accuracy 
                                # as in the csv file
                                rp_pt = round_pt_2_cm(vtx_feat_pt_cc)
                                elim_dbpt.append(rp_pt)
                                elim_pts.append(elim_dbpt)
                                to_create = False     
                            m_box.exec_()
                # Creation of the RFU objects in the layers
                if to_create:
                    create_nw_feat( self.l_vertex, 
                                    QgsGeometry.fromPointXY(nw_pt_wgs), 
                                    [NULL, NULL, ge_createur, som_delim_pub, pt_type, pt_type_cmt, idx_prec, float("{0:.02f}".format(nw_pt.x())), float("{0:.02f}".format(nw_pt.y())), self.cc, 0.0, "false", id_ptintol]
                                    )                    

            # Creation of limits
            self.iface.setActiveLayer(self.l_vertex)
            self.iface.setActiveLayer(self.l_edge)
            for lim in nw_edge:
                start_pt_cc = lim[0]
                end_pt_cc = lim[1]
                # Check if the point is an eliminated point
                # If yes, use the corresponding RFU point instead
                for elim_pt in elim_pts:
                    if start_pt_cc == elim_pt[0]:
                        start_pt_cc = elim_pt[1]
                    if end_pt_cc == elim_pt[0]:
                        end_pt_cc = elim_pt[1]
                
                # Creation only if no double point
                if check_no_dblpt(start_pt_cc, end_pt_cc):
                    start_pt = coords_trf_wgs.transform(start_pt_cc)
                    end_pt = coords_trf_wgs.transform(end_pt_cc)
                    # Create line geometry
                    line = QgsGeometry.fromPolylineXY([start_pt, end_pt])
                    # Check if the lines intersects
                    to_create = check_limit_cross(line, self.original_l_edge,ge_createur, lim[2], lim[3], self.canvas, True)
                    # Creation of the new RFU objects in the layer
                    if to_create:
                        # Create the feature
                        create_nw_feat(self.l_edge, line, [NULL, NULL, ge_createur, lim[2], lim[3]])                      
                
            # Refresh the canvas
            self.canvas.refresh()