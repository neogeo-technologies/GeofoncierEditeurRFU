#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-


# Copyright (C) 2015 Géofoncier (R)


import xml.etree.ElementTree as EltTree

from urlparse import urljoin

import tools
from config import Configuration


class APIClient(object):

    def __init__(self, base_url=None, user_agent=None,
                 user=None, pw=None):

        self.config = Configuration()

        self.base_url = base_url or self.config.base_url
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

    def get_my_capabilities(self):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/getCapaKey_get_1`

        """
        url = urljoin(self.base_url, r"rfuoge/getmycapabilities")
        return tools.request(url, user_agent=self.user_agent,
                             user=self.user, password=self.pw)

    def get_capabilities(self, zone):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/getNomenclatureRFU_get_0`

        """
        url = urljoin(self.base_url, r"rfuoge/getcapabilities")
        return tools.request(url, user_agent=self.user_agent, user=self.user,
                             password=self.pw, params={r"zone": zone})

    def extraction(self, xmin, ymin, xmax, ymax):
        """See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/extractRFU_get_2`

        """
        url = urljoin(self.base_url, r"rfuoge/extraction")
        return tools.request(
                    url, user_agent=self.user_agent,
                    user=self.user, password=self.pw,
                    params={r"bbox": r"%s,%s,%s,%s" % (xmin, ymin, xmax, ymax)})

    def open_changeset(self, zone, data={}):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/createChangeset_post_5`

        """
        url = urljoin(self.base_url, r"rfuoge/changeset")
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, params={r"zone": zone}, data=data)

    def close_changeset(self, zone, id):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/closeChangeset_put_6`

        """
        url = urljoin(self.base_url, r"rfuoge/changeset/%s%s" % (zone[0], id))
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, method=r"PUT",
                    params={r"request": r"close", "id_changeset": id})

    def edit(self, zone, data):
        """"See..
        `https://api.geofoncier.fr/documentation/#!/rfuoge/editRFU_post_7`

        """
        url = urljoin(self.base_url, r"rfuoge/edit")
        return tools.request(
                    url, user_agent=self.user_agent, user=self.user,
                    password=self.pw, params={r"zone": zone}, data={r"xml": data})
