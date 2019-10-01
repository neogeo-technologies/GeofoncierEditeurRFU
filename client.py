# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Editor RFU Geofoncier
    * Description:   Client
    * First release: 2015
    * Last release:  2019-08-19
    * Copyright:     (C) 2015 Géofoncier(R), (C) 2019 SIGMOÉ(R),Géofoncier(R)
    * Email:         em at sigmoe.fr
    * License:       Proprietary license
    ***************************************************************************
"""


import xml.etree.ElementTree as EltTree
from urllib.parse import urljoin

from . import tools
from .config import Configuration


class APIClient:

    def __init__(self, base_url=None, base_url_rfu=None,
                 user_agent=None, user=None, pw=None):

        self.config = Configuration()

        self.base_url = base_url or self.config.base_url
        self.base_url_rfu = base_url_rfu or self.config.base_url_rfu
        self.user_agent = user_agent or self.config.user_agent
        self.user = user # or self.config.user
        self.pw = pw # or self.config.pw

        self.extract = False
        self.extract_lim = 0
        self.update = False

        resp = self.referentielsoge_ge()
        if resp.code != 200:
            return

        tree = EltTree.fromstring(resp.read())
        self.nom = tree.find(r"./ge/nom").text
        self.prenom = tree.find(r"./ge/prenom").text

    def referentielsoge_ge(self):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/referentielsoge/getInfoGE_get_2`

        """
        url = urljoin(self.base_url, r"referentielsoge/ge")
        return tools.request(url, user_agent=self.user_agent, user=self.user,
                             password=self.pw, params={r"numero": self.user})

    def dossiersoge_dossiers(self, zone, enr_ref_dossier):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/dossiersoge/getDossiers_get_5`

        """
        url = urljoin(self.base_url, r"dossiersoge/dossiers")
        return tools.request(
                    url, user_agent=self.user_agent,
                    user=self.user, password=self.pw,
                    params={r"zone": zone, r"enr_ref_dossier": enr_ref_dossier})

    def get_my_capabilities(self):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/getCapaKey_get_1`

        """
        url = urljoin(self.base_url_rfu, r"rfuoge/getmycapabilities")
        return tools.request(url, user_agent=self.user_agent,
                             user=self.user, password=self.pw)

    def get_capabilities(self, zone):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/getNomenclatureRFU_get_0`

        """
        url = urljoin(self.base_url_rfu, r"rfuoge/getcapabilities")
        return tools.request(url, user_agent=self.user_agent, user=self.user,
                             password=self.pw, params={r"zone": zone})

    def extraction(self, xmin, ymin, xmax, ymax):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/extractRFU_get_2`

        """
        url = urljoin(self.base_url_rfu, r"rfuoge/extraction")
        return tools.request(
                    url, user_agent=self.user_agent,
                    user=self.user, password=self.pw,
                    params={r"bbox": r"%s,%s,%s,%s" % (xmin, ymin, xmax, ymax)})

    def open_changeset(self, zone, enr_api_dossier=None, commentaire=None, data=r""):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/createChangeset_post_5`

        """
        params={r"zone": zone}
        if enr_api_dossier:
            params[r"enr_api_dossier"] = enr_api_dossier
        if commentaire:
            params[r"commentaire"] = commentaire

        url = urljoin(self.base_url_rfu, r"rfuoge/changeset")
        return tools.request(
                url, user_agent=self.user_agent, user=self.user,
                password=self.pw, params=params, data=data)

    def close_changeset(self, zone, id):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/closeChangeset_put_6`

        """

        if zone == r"mayotte":
            zone = "y"

        url = urljoin(self.base_url_rfu, r"rfuoge/changeset/%s%s" % (zone[0], id))
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, method=r"PUT",
                    params={r"request": r"close", "id_changeset": id})

    def edit(self, zone, data):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/editRFU_post_7`

        """
        url = urljoin(self.base_url_rfu, r"rfuoge/edit")
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, params={r"zone": zone}, data={r"xml": data})

    def get_ptplots(self, id_node, zone):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/getSommetDeterminations_get_15`

        """
        url = urljoin(self.base_url_rfu, r"rfuoge/sommet/%s" % id_node)
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, 
                    params={"id_sommet": id_node, 
                            "r": 'determination',
                            "zone": zone})
                                     
    def cancel_plot(self, id_som, id_det, zone):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/cancelSommetDeterminations_put_16`

        """

        url = urljoin(self.base_url_rfu, r"rfuoge/sommet/%s" % (id_som))
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, method=r"PUT",
                    params={"r": 'determination',
                            "id": id_det,
                            "statut": 'cancel',
                            "zone": zone})