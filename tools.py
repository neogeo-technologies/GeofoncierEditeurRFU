# -*- coding: utf-8 -*-

"""
    ***************************************************************************
    * Plugin name:   GeofoncierEditeurRFU
    * Plugin type:   QGIS 3 plugin
    * Module:        Tools
    * Description:   Define a class that provides to the plugin
    *                GeofoncierEditeurRFU several tools
    * First release: 2015
    * Last release:  2022-01-10
    * Copyright:     (C) 2019,2020,2021, 2022 GEOFONCIER(R), SIGMOÉ(R)
    * Email:         em at sigmoe.fr
    * License:       GPL license
    ***************************************************************************
"""


from qgis.PyQt.QtCore import Qt, QDateTime, QDate
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                        QgsRectangle, QgsFeatureRequest)
                        
import base64
import unicodedata
import urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ElementTree

from .global_fnc import *


def request(url, method=None, user_agent=None, access_token=None, params=None, data=None, content_type=None):

    if params:
        url = r"%s?%s" % (url, urllib.parse.urlencode(params))
        
    if data is not None:
        data = urllib.parse.urlencode(data)
        # data must be passed as bytes when used with urlopen
        data = data.encode('ascii')
        

    req = urllib.request.Request(url, data)

    if method == r"PUT":
        req.get_method = lambda: r"PUT"
    if user_agent:
        req.add_header(r"User-agent", user_agent)
    if access_token:
        req.add_header(r"Authorization", r"Bearer %s" % access_token)
    
    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as err:
        return err
    except urllib.error.URLError:
        raise
        
def get_token(url, method=None, user_agent=None, user=None,
            password=None, params=None, data=None, content_type=None):

    if params:
        url = r"%s?%s" % (url, urllib.parse.urlencode(params))
        
    if data is not None:
        data = urllib.parse.urlencode(data)
        # data must be passed as bytes when used with urlopen
        data = data.encode('ascii')

    req = urllib.request.Request(url, data)

    if method == r"PUT":
        req.get_method = lambda: r"PUT"

    if user and password:
        base64string = base64.encodebytes(("%s:%s" % (user, password)).encode('utf-8')).decode('utf-8')[:-1]
        req.add_header(r"Authorization", r"Basic %s" % base64string)

    if user_agent:
        req.add_header(r"User-agent", user_agent)

    try:
        return urllib.request.urlopen(req)
    except urllib.error.HTTPError as err:
        return err
    except urllib.error.URLError:
        raise

def reproj(qgsgeom, crs_in, crs_out, project):
    """Simple reprojector..

    qgsgeom -> QgsGeometry() object
    crs_in -> input CRS in EPSG (e.g. 3857)
    crs_out -> output CRS in EPSG (e.g. 4326)

    """
    x_crs_type = QgsCoordinateReferenceSystem.EpsgCrsId
    x_crs_in = QgsCoordinateReferenceSystem(crs_in, x_crs_type)
    x_crs_out = QgsCoordinateReferenceSystem(crs_out, x_crs_type)
    x = QgsCoordinateTransform(x_crs_in, x_crs_out, project)

    # Spefic case for bbox..
    if type(qgsgeom) == QgsRectangle:
        return x.transformBoundingBox(qgsgeom)

    # This is the default..
    return x.transform(qgsgeom)

def get_feature_by_id(qgslayer, qgsft_fid):
    """Return QgsFeature() corresponding to fid..

    qgslayer -> QgsVectorLayer()
    qgsft_fid -> QgsFeature().id()

    """
    request = QgsFeatureRequest().setFilterFid(qgsft_fid)
    return next(feature for feature in qgslayer.getFeatures(request))

def attrib_as_kv(qgsfields, qgsft_attributes, qgsgeom=None):
    """Return attributes as a dict {<field>: <value>}..

    qgsfields -> QgsFields()
    qgsft_attributes -> QgsFeature().attributes()
    qgsgeom -> QgsGeometry()

    """
    for i, e in enumerate(qgsft_attributes):
        if type(e) == QDate:
            qgsft_attributes[i] = e.toString(Qt.ISODate)
        if type(e) == QDateTime:
            qgsft_attributes[i] = e.toString(Qt.ISODate)
        if not e:
            qgsft_attributes[i] = r""

    fields = [field.name() for field in qgsfields.toList()]

    attrib = {}
    for i, e in enumerate(fields):
        attrib[e] = qgsft_attributes[i]
    if qgsgeom:
        attrib[r"@geometrie"] = qgsgeom.asWkt()

    return attrib

def xml_subelt_creator(root, tag, data, action=None):
    """Return a XML sub-element..

    tag -> str
    data -> dict
    action -> str

    """
    attrib = {}
    for key in data:
        if key.startswith(r"@"):
            attrib[key[1:]] = str(data[key])
    if action:
        attrib[r"action"] = action

    elt = ElementTree.SubElement(root, tag, attrib=attrib)

    for key in data:
        val = data[key]
        if not key.startswith(r"@"):
            ElementTree.SubElement(elt, key).text = str(val) 
    return elt
