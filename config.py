# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Config
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU the Configuration
    * First release: 2015
    * Last release:  2021-03-12
    * Copyright:     (C) 2019,2020,2021 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license 
    ***************************************************************************
"""


import os
import json
from .global_fnc import *


class Configuration:

    def __init__(self):
        try:
            self.path = os.path.join(os.path.dirname(__file__), r"config.json")
        except IOError as error:
            raise error

        self.config = self.load()

        self.config_api = self.config[r"api"]

        self.base_url = None
        if r"url" in self.config_api:
            self.base_url = str(self.config_api[r"url"])

        self.base_url_rfu = None
        if r"url_rfu" in self.config_api:
            self.base_url_rfu = str(self.config_api[r"url_rfu"])

        self.user_agent = None
        if r"user_agent" in self.config_api:
            self.user_agent = str(self.config_api[r"user_agent"])

        self.user = None
        if r"user" in self.config_api:
            self.user = str(self.config_api[r"user"])

        self.pw = None
        # To clean old config.json
        if r"password" in self.config_api:
            del self.config_api[r"password"]
            self.save(data=self.config)
        
        self.access_token = None
        if r"access_token" in self.config_api:
            self.access_token = str(self.config_api[r"access_token"])
            
    def load(self):
        """Return the yaml configuration file.."""
        with open(self.path, r"r") as that:
            return json.load(that)

    def save(self, data):
        """Save the yaml configuration file..

        data -> dict

        """
        with open(self.path, r"w") as this:
            this.write(json.dumps(data, indent=4, separators=(',', ': ')))

    def set_login_info(self, user, password):
        """Save login informations in plain text..

        user -> str
        password -> str

        """
        self.config_api[r"user"] = user
        self.save(data=self.config)
        
    def set_token_info(self, token):
        """Save token in plain text..

        token -> str

        """
        self.config_api[r"access_token"] = token
        self.save(data=self.config)

    def erase_login_info(self):
        """Erase login informations.."""
        if r"user" in self.config_api:
            self.config_api.pop(r"user")

        if r"password" in self.config_api:
            self.config_api.pop(r"password")

        self.save(data=self.config)
