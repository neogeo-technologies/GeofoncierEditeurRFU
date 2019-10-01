# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS plugin
    * Module:        Global Vars
    * Description:   Global variables
    * First release: 2018-07-16
    * Last release:  2019-09-24
    * Copyright:     (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField

# Interface messages
mnu_title_txt = "Géofoncier Éditeur RFU"

# Dialog box variables
tl_csv_choice = "Choisir le fichier CSV à importer"
tl_imp_canc = "Import annulé"
txt_csvimp_canc = "Vous n'avez pas sélectionné de fichier CSV ! \nImport annulé !"
txt_csvimp_norfu_canc = "Vous devez d'abord télécharger les données du RFU avant d'effectuer un import du fichier CSV.\nImport CSV annulé !"
tl_dxf_choice = "Choisir le fichier DXF à importer"
txt_dxfimp_canc = "Vous n'avez pas sélectionné de fichier DXF ! \nImport annulé !"
txt_dxfimp_norfu_canc = "Vous devez d'abord télécharger les données du RFU avant d'effectuer un import du fichier DXF.\nImport DXF annulé !"
tl_pt_exst_rfu = "Point proche d'un point déjà présent dans le RFU"
txt_pt_exst_rfu = "<b>Un point importé est proche (dans la tolérance) d'un point RFU !</b>"
inftxt_pt_exst_rfu = "Le point importé aux coordonnées:<br/>{0:.2f},{1:.2f}<br/>se situe à moins de {2:.3f} mètres du point existant n° {3:d} (dans le tolérance du sommet existant) .<br/>Le point nouveau est créé comme <font color=\"firebrick\">Point nouveau à traiter car proche d'un existant</font>, mais il devra être contrôlé pour éventuellement être transformé en nouvelle détermination du point existant."
tl_pt_dbl = "Point doublon dans l'import"
txt_pt_dbl = "<b>Un point semble être en double dans le fichier importé !</b>"
inftxt_pt_dbl = "Le point aux coordonnées:<br/>{0:.2f},{1:.2f}<br/>se situe aux mêmes coordonnées qu'un autre point issu de l'import.<br/>Ce nouveau point est donc considéré comme un doublon et ne sera pas créé!"
tl_ptrfu_dbl = "Point doublon avec un point existant"
txt_ptrfu_dbl = "<b>Un point importé est strictement identique à un point existant dans le RFU !</b>"
inftxt_ptrfu_dbl = "Le point aux coordonnées:<br/>{0:.2f},{1:.2f}<br/>se situe aux mêmes coordonnées que le point n° {2:d} du RFU.<br/>Le point aux coordonnées:\n{0:.2f},{1:.2f} a été éliminé !"
txt_nwpt_exst_rfu = "<b>Le point à créer est proche (dans la tolérance) d'un point RFU !</b>"
inftxt_nwpt_exst_rfu = "Le point à créer se situe à moins de {0:.3f} mètres du point existant n° {1:d} (dans le tolérance du sommet existant) .<br/>Le point nouveau est créé comme <font color=\"firebrick\">Point nouveau à traiter car proche d'un existant</font>, mais il devra être contrôlé pour éventuellement être transformé en nouvelle détermination du point existant."
txt_nwpt_rfu_dbl = "<b>Le point à créer existe déjà dans le RFU !</b>"
inftxt_nwpt_rfu_dbl = "Le point à créer se situe aux mêmes coordonnées que le point n° {0:d} du RFU.<br/>Le point à créer ne sera pas créé !"
tl_nwpt_dbl = "Création d'un point double"
txt_nwpt_dbl = "<b>Le point à créer existe déjà parmi les points nouvellement créés !</b>"
inftxt_nwpt_dbl = "Le point à créer se situe aux mêmes coordonnées qu'un autre point déjà créé.<br/>Ce nouveau point est donc considéré comme un doublon et ne sera pas créé."
tl_ln_exst_rfu = "Point déjà présent dans le RFU"

tl_ln_ints = "Intersection de lignes"
txt_ln_ints = "<b>Deux limites importées s'intersectent !</b>"
inftxt_ln_ints = "La deuxième limite a été placée dans la couche <font color=\"firebrick\">{0:s}</font> et ne sera pas exportée.\nVous devez corriger le problème !"
txt_ln_ints_rfu = "<b>Une limite importée intersecte une limite du RFU !</b>"
inftxt_ln_ints_rfu = "La limite importée a été placée dans la couche <font color=\"firebrick\">{0:s}</font> et ne sera pas exportée.\nVous devez corriger le problème !"
txt_nwln_ints = "<b>La nouvelle limite intersecte une autre nouvelle limite !</b>"
txt_nwln_ints_rfu = "<b>La nouvelle limite intersecte une limite du RFU !</b>"
inftxt_nwln_ints = "La limite en cours de création ne sera pas créée !"

tl_ln_equ = "Limites dupliquées"
txt_ln_equ = "<b>Deux limites importées sont stricitement identiques !</b>"
inftxt_ln_equ = "La deuxième limite a été éliminée !"
txt_ln_equ_rfu = "<b>Une limite importée est strictement identique à une limite du RFU !</b>"
inftxt_ln_equ_rfu = "La limite importée a été élimminée !"
txt_nwln_equ = "<b>La nouvelle limite est strictement identique à une autre nouvelle limite !</b>"
txt_nwln_equ_rfu = "<b>La nouvelle limite est strictement identique à une limite du RFU !</b>"
inftxt_nwln_equ = "La limite en cours de création ne sera pas créée !"

tl_atn = "Attention"
txt_msg_outbbox = "<b>Eléments nouveaux hors zone !</b>"
msg_outbbox_vtx = "Un ou plusieurs sommets nouveaux se trouvent hors de la zone de travail ! <br/>Ils ont été déplacés dans la couche <font color=\"firebrick\">{0:s}</font> et n'ont pas été exportés."
msg_outbbox_edge = "Une ou plusieurs limites nouvelles se trouvent hors de la zone de travail !<br/>Elles ont été déplacées dans la couche <font color=\"firebrick\">{0:s}</font> et n'ont pas été exportées."

msg_obt_det_imp = "Obtention déterminations impossible"
msg_obt_cap_imp = "Obtention paramètres impossible"
msg_obt_cap_ident = "Veuillez vous identifier !"

plot_dif_txt = {    "info": [
                            "Consultation déterminations",
                            "Cliquez sur un sommet pour voir apparaitre ses déterminations",
                            "Liste des déterminations du sommet n° %s"
                            ],
                    "del": [
                            "Suppression détermination",
                            "Cliquez sur un sommet, puis cliquez sur la détermination à supprimer dans la liste",
                            "Liste des déterminations du sommet n° %s - Cliquez sur la ligne de la détermination à supprimer"
                            ]
               }
plot_no_del_msg = [ "Détermination non supprimable",
                    "<b>Une seule détermination valide ! Détermination non supprimée.</b>", 
                    "Le sommet cliqué ne contient qu'une seule détermination valide.<br>Pour supprimer la détermination, vous devez supprimer le sommet."
                    ]
                    
plot_notrfusel_msg = [   msg_obt_det_imp,
                        "Le point cliqué est un sommet nouveau et non un sommet RFU !\nVous devez cliquer sur un sommet RFU pour pouvoir obtenir ses déterminations."
                        ]
                    
tl_plot_delimp = "Suppression détermination impossible"
tl_plot_delok = "Suppression détermination réussie"
msg_plot_delok = "Suppression de la détermination réalisée avec succès !"
msg_plotcancd_del = "Détermination déjà annulée !\nVeuillez choisir une autre détermination à supprimer."
tl_plot_delimp_sure = "Validation suppression détermination"
msg_plot_delimp_sure = "Vous êtes sur le point de supprimer définitivement la détermination sélectionnée.<br/><b>Validez-vous la suppression définitive de cette détermination ?</b>"

tr_vtxplt_nolinesel_msg = [ "Validation impossible",
                            "Vous devez sélectionner une ligne dans la liste avant de valider le sommet sélectionné !"
                            ]
tr_vtxplt_valid_msg = [ "Validation OK", 
                        "Sommet aux coordonnées\n{0:.2f},{1:.2f}\nvalidé !"
                        ]
tr_pttoplot_imp_msg = [ "Traitement impossible",
                        "Vous devez d'abord télécharger les données du RFU !"
                        ]
tr_vtxplt_sel_nolinesel_msg = [ "Sélection sommet RFU impossible",
                            "Vous devez sélectionner une ligne dans la liste avant de valider le sommet sélectionné !"
                            ]
tr_vtxplt_sel_nonwvtxsel_msg = [ "Sélection sommet RFU impossible",
                            "Vous devez d'abord sélectionner un sommet nouveau avant de sélectionner un sommet RFU !"
                            ]
tr_vtxplt_notrfuvtx_msg = [ "Mauvais choix de sommet",
                            "Vous n'avez pas choisi un sommet déjà existant dans le RFU !\nVeuillez choisir un sommet RFU."
                            ]
tr_vtxplt_notnwvtx_msg = [ "Mauvais choix de sommet",
                            "Vous n'avez pas choisi un sommet nouvellement créé!\nVeuillez choisir un nouveau sommet."
                            ]
tr_vtxplt_confirm_msg = [ "Confirmation",
                          "Vous êtes sur le point de transformer le sommet nouveau situé aux coordonnées\n{0:.2f},{1:.2f}\nen nouvelle détermination du point RFU n°{2:d}.\nConfirmez-vous cette transformation ?"
                          ]
tr_vtxplt_attest_msg = [ "Confirmation avec attestation de qualité",
                          "Vous êtes sur le point de transformer le sommet nouveau situé aux coordonnées {0:.2f},{1:.2f} en nouvelle détermination du point RFU n°{2:d}.<br/><b><font color=\"red\">ATTENTION: La distance entre la nouvelle détermination versée et la position actuelle du sommet RFU ({3:.2f} cm) est supérieure à la tolérance admise pour ce sommet RFU ({4:.2f} cm)</font></b>.<br/>En confirmant la création de cette nouvelle détermination, vous ajoutez la mention :<br/><b><center>J'atteste de la qualité de la détermination</center></b><br/>Confirmez-vous cette nouvelle détermination avec votre attestion de qualité ?"
                          ]
tr_vtxplt_canceld_msg = [   "Annulation",
                            "Opération annulée !"
                            ]
tr_vtxplot_nosamerp_msg = [ "Transformation impossible",
                            "Le sommet nouveau et le sommet RFU à redéterminer ne sont pas définis dans le même système de coorodnnées !\nLa transformation est donc annulée."
                            ]
tr_vtxplot_transfok_msg = [ "Transformation réalisée avec succès",
                            "Le sommet nouveau situé aux coordonnées\n{0:.2f},{1:.2f}\na été transformé en nouvelle détermination du point RFU n°{2:d}."
                            ]
                            
multi_doss_canceled_msg = [ "Envoi annulé",
                            "Vous n'avez pas choisi de référence dossier !\nEnvoi annulé."
                            ]

reinit_msg =[   "Réinitialisation de l'espace de travail",
                "La réinitialisation de l'espace de travail provoque l'effacement de tous les objets nouvellement créés dans la zone de travail.<br/><b>Cette action est irréversible.</b><br/>Êtes-vous sûr de vouloir réinitialiser l'espace de travail ?"
                ]

# Comment default text
cmt_dft = "Versement depuis QGIS - Dossier %s"

# Message for DXF Import block choice
no_blk = "Pas de bloc associé"
# Message for all blocks DXF Import)
all_blks = "Tous les blocs du calque"
# LineEdit placeholder text for new nature
le_phtxt = "Nature personnalisée"

# Parameters of the layer created for eliminated limits
elimedge_mono = False
elimedge_lname = "Limite éliminée (non exportable)"
elimedge_col = '#ff4201'
elimedge_col2 = '#ffa500'
elimedge_opc = 0.7
elimedge_wdt = 1.0
inter_rfu = "Intersecte une limite du RFU"
inter_new = "Intersecte une limite nouvelle"

# Parameters of the layer created for the vertices out of the bbox when exporting
vtx_outofbbox_lname = "Sommets hors zone"
vtx_outofbbox_color = '#ffb7b7'
vtx_outofbbox_size = 2.5
vtx_outofbbox_opc = 0.7

# Parameters of the layer created for the edges out of the bbox when exporting
edge_outofbbox_lname = "Limites hors zone"
edge_outofbbox_color = '#ffb7b7'
edge_outofbbox_width = 1.0
edge_outofbbox_opc = 0.7

# Parameters for scale check of imported area
scale_limit = 5000
wrong_scale_txt = "L'échelle du permalien est trop grande ! Elle ne doit pas être supérieure à {0:s}."

# Parameter for scale limit in the canvas
cvs_scale_limit = 25000

# List of headers of the capabilities table (in the desired order displayed)
# Each  item is a list [index of variable, text of header]
captbl_table_hd = [ 
                    [0, "Système géodésique"],
                    [1, "Classes de précision de rattachement"], 
                    [2, "Représentations planes acceptées"], 
                    [3, "Natures de sommet conseillées"], 
                    [4, "Géomètres-experts modificateurs"], 
                    [5, "Tolérance points identiques"]
                  ]

# List of headers of the pt plots table (in the desired order displayed)
# Each  item is a list [index of variable, text of header]
ptplottbl_table_hd = [  
                        [0, "Identifiant détermination"],
                        [1, "GE créateur"], 
                        [2, "Coord. EST"], 
                        [3, "Coord. NORD"], 
                        [4, "Classe de précision"], 
                        [5, "Système de coordonnées"],
                        [6, "Date détermination"],
                        [7, "Distance à la position de référence"],
                        [8, "Tolérance"],
                        [9, "Attestation de qualité"],
                        [10, "Changeset associé"],
                        [11, "Statut"],
                        [12, "Date d'annulation"]
                      ]
                      
rpl_true = ["True", "Valide", "Oui"]
rpl_false = ["False", "Annulée", "Non"]
st_true_bkgcol = '#b6ffa7'
st_false_bkgcol = '#ffa7a7'

                    
# List of attributes for vertex and edge layers
vtx_atts = [
                QgsField(r"@id_noeud", QVariant.LongLong),
                QgsField(r"@version", QVariant.Int),
                QgsField(r"som_ge_createur", QVariant.String),
                QgsField(r"som_nature", QVariant.String),
                QgsField(r"som_precision_rattachement", QVariant.Int),
                QgsField(r"som_coord_est", QVariant.Double),
                QgsField(r"som_coord_nord", QVariant.Double),
                QgsField(r"som_representation_plane", QVariant.String),
                QgsField(r"som_tolerance", QVariant.Double),
                QgsField(r"attestation_qualite", QVariant.String),
                QgsField(r"point_rfu_proche", QVariant.LongLong)
            ]
edge_atts = [
                QgsField(r"@id_arc", QVariant.LongLong),
                QgsField(r"@version", QVariant.Int),
                QgsField(r"lim_ge_createur", QVariant.String)
            ]
            
# List of attributes to transfer in case of new vertex to plot
tr_toplot_atts = [
                "som_ge_createur",
                "som_nature",
                "som_precision_rattachement",
                "som_coord_est",
                "som_coord_nord",
                "som_representation_plane"
            ]
# List of attributes to show when transforming new point to plot
tr_vtx_atts = list(tr_toplot_atts)
tr_vtx_atts.append("point_rfu_proche")
            
# Default size of dlgs
dlg_show_capabilities_sw = 1000
dlg_show_capabilities_sh = 400
dlg_show_ptplots_sw = 1000
dlg_show_ptplots_sh = 400
dlg_transfo_pt_to_plots_sw = 973
dlg_transfo_pt_to_plots_sh = 400
