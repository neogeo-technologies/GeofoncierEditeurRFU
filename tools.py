#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (C) 2015 Géofoncier (R)


import base64
import unicodedata
import urllib
import urllib2
import xml.etree.ElementTree as ElementTree

from PyQt4.QtCore import Qt
from PyQt4.QtCore import QDateTime
from PyQt4.QtCore import QDate
from PyQt4.QtCore import QPyNullVariant
from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsRectangle
from qgis.core import QgsFeatureRequest


def request(url, method=None, user_agent=None, user=None,
            password=None, params=None, data=None, content_type=None):

    if params:
        url = r"%s?%s" % (url, urllib.urlencode(params))

    if data is not None:
        data = urllib.urlencode(data)

    req = urllib2.Request(url, data)

    if method == r"PUT":
        req.get_method = lambda: r"PUT"

    if user and password:
        base64string = base64.encodestring("%s:%s" % (user, password))[:-1]
        req.add_header(r"Authorization", r"Basic %s" % base64string)

    if user_agent:
        req.add_header(r"User-agent", user_agent)

    try:
        return urllib2.urlopen(req)
    except urllib2.HTTPError, err:
        return err
    except urllib2.URLError:
        raise


def reproj(qgsgeom, crs_in, crs_out):
    """Simple reprojector..

    qgsgeom -> QgsGeometry() object
    crs_in -> input CRS in EPSG (e.g. 3857)
    crs_out -> output CRS in EPSG (e.g. 4326)

    """
    x_crs_type = QgsCoordinateReferenceSystem.EpsgCrsId
    x_crs_in = QgsCoordinateReferenceSystem(crs_in, x_crs_type)
    x_crs_out = QgsCoordinateReferenceSystem(crs_out, x_crs_type)
    x = QgsCoordinateTransform(x_crs_in, x_crs_out)

    # Spefic case for bbox..
    if type(qgsgeom) == QgsRectangle:
        return x.transformBoundingBox(qgsgeom)

    # This is the default..
    return x.transform(qgsgeom)


#def acronym_to_epsg(acronym):
#
#    d = {r"RGF93CC42": 3942,
#         r"RGF93CC43": 3943,
#         r"RGF93CC44": 3944,
#         r"RGF93CC45": 3945,
#         r"RGF93CC46": 3946,
#         r"RGF93CC47": 3947,
#         r"RGF93CC48": 3948,
#         r"RGF93CC49": 3949,
#         r"RGF93CC50": 3950}
#
#    return d[acronym]


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
        if type(e) == QPyNullVariant:
            qgsft_attributes[i] = r""

    fields = [field.name() for field in qgsfields.toList()]

    attrib = {}
    for i, e in enumerate(fields):
        attrib[e] = qgsft_attributes[i]
    if qgsgeom:
        attrib[r"@geometrie"] = qgsgeom.exportToWkt()

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
        if type(val) is unicode:
            val = unicodedata.normalize(r'NFKD', data[key]).encode(r'ascii', r'ignore')
        if not key.startswith(r"@"):
            ElementTree.SubElement(elt, key).text = str(val)
    return elt
