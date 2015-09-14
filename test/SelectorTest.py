#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2012-2014 DESY, Jan Kotanski <jkotan@mail.desy.de>
#
#    nexdatas is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    nexdatas is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with nexdatas.  If not, see <http://www.gnu.org/licenses/>.
## \package test nexdatas
## \file SelectorTest.py
# unittests for TangoDsItemTest running Tango Server
#
import unittest
import os
import sys
import subprocess
import random
import struct
import threading
import binascii
import Queue
import PyTango
import json
import pickle
import string
import time

import logging
logger = logging.getLogger()

import TestMacroServerSetUp
import TestPoolSetUp
import TestServerSetUp
import TestConfigServerSetUp
import TestWriterSetUp


from nxsrecconfig.MacroServerPools import MacroServerPools
from nxsrecconfig.Selector import Selector
from nxsrecconfig.Utils import TangoUtils, MSUtils
from nxsconfigserver.XMLConfigurator import XMLConfigurator

## if 64-bit machione
IS64BIT = (struct.calcsize("P") == 8)

## list of available databases
DB_AVAILABLE = []

try:
    import MySQLdb
    ## connection arguments to MYSQL DB
    mydb = MySQLdb.connect({})
    mydb.close()
    DB_AVAILABLE.append("MYSQL")
except:
    try:
        import MySQLdb
    ## connection arguments to MYSQL DB
        args = {'host': u'localhost', 'db': u'nxsconfig',
                'read_default_file': u'/etc/my.cnf', 'use_unicode': True}
    ## inscance of MySQLdb
        mydb = MySQLdb.connect(**args)
        mydb.close()
        DB_AVAILABLE.append("MYSQL")
    except:
        try:
            import MySQLdb
            from os.path import expanduser
            home = expanduser("~")
        ## connection arguments to MYSQL DB
            args2 = {'host': u'localhost', 'db': u'nxsconfig',
                     'read_default_file': u'%s/.my.cnf' % home,
                     'use_unicode': True}
        ## inscance of MySQLdb
            mydb = MySQLdb.connect(**args2)
            mydb.close()
            DB_AVAILABLE.append("MYSQL")

        except ImportError, e:
            print "MYSQL not available: %s" % e
        except Exception, e:
            print "MYSQL not available: %s" % e
        except:
            print "MYSQL not available"


## test fixture
class SelectorTest(unittest.TestCase):

    ## constructor
    # \param methodName name of the test method
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

        self._bint = "int64" if IS64BIT else "int32"
        self._buint = "uint64" if IS64BIT else "uint32"
        self._bfloat = "float64" if IS64BIT else "float32"

        self._ms = TestMacroServerSetUp.TestMacroServerSetUp()
        self._cf = TestConfigServerSetUp.TestConfigServerSetUp()
        self._wr = TestWriterSetUp.TestWriterSetUp()
        self._pool = TestPoolSetUp.TestPoolSetUp()
        self._simps = TestServerSetUp.TestServerSetUp()

        try:
            self.__seed = long(binascii.hexlify(os.urandom(16)), 16)
        except NotImplementedError:
            self.__seed = long(time.time() * 256)

        self.__rnd = random.Random(self.__seed)

        self.__dump = {}

        ## default zone
        self.__defaultzone = 'Europe/Berlin'
        ## default mntgrp
        self.__defaultmntgrp = 'nxsmntgrp'
        ## default path
        self.__defaultpath = \
            '/entry$var.serialno:NXentry/NXinstrument/collection'

        self._keys = [
            ("Timer", '[]'),
            ("OrderedChannels", '[]'),
            ("ComponentGroup", '{}'),
            ("AutomaticComponentGroup", '{}'),
            ("AutomaticDataSources", '[]'),
            ("DataSourceGroup", '{}'),
            ("InitDataSources", '[]'),
            ("OptionalComponents", '[]'),
            ("AppendEntry", False),
            ("ComponentsFromMntGrp", False),
            ("ConfigVariables", '{}'),
            ("DataRecord", '{}'),
            ("Labels", '{}'),
            ("LabelPaths", '{}'),
            ("LabelLinks", '{}'),
            ("HiddenElements", '[]'),
            ("LabelTypes", '{}'),
            ("LabelShapes", '{}'),
            ("DynamicComponents", True),
            ("DynamicLinks", True),
            ("DynamicPath", self.__defaultpath),
            ("TimeZone", self.__defaultzone),
            ("ConfigDevice", ''),
            ("WriterDevice", ''),
            ("Door", ''),
            ("MntGrp", '')
            ]

        self.mysel = {
            'mysl': (
                '{}'),
            'mysl2': (
                json.dumps({key: value for (key, value) in self._keys})),
            }

        self.mycps = {
            'mycp': (
                '<?xml version=\'1.0\'?>'
                '<definition>'
                '<group type="NXcollection" name="dddd"/>'
                '</definition>'),
            'mycp2': (
                '<definition><group type="NXcollection" name="dddd">'
                '<field><datasource type="TANGO" name="ann" /></field>'
                '</group></definition>'),
            'mycp3': (
                '<definition><group type="NXcollection" name="dddd">'
                '<field><datasource type="TANGO" name="ann" />'
                '<strategy mode="STEP" />'
                '</field></group></definition>'),
            'exp_t01': (
                '<?xml version=\'1.0\'?>'
                '<definition>'
                '<group type="NXentry" name="entry1">'
                '<group type="NXinstrument" name="instrument">'
                '<group type="NXdetector" name="detector">'
                '<field units="s" type="NX_FLOAT" name="exp_t01">'
                '<strategy mode="STEP"/>'
                '<datasource type="CLIENT" name="exp_t01">'
                '<record name="haso228k:10000/expchan/dgg2_exp_01/1"/>'
                '</datasource></field></group></group>'
                '</group></definition>'),
            'dim1': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="1">'
                '<dim index="1" value="34">'
                '</dim></dimensions>'
                '</field></group>'
                '</definition>'),
            'dim2': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="1">'
                '<dim index="1" value="$datasource.ann">'
                '</dim></dimensions>'
                '</field></group>'
                '</definition>'),
            'dim3': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="1">'
                '<dim index="1">1234'
                '</dim></dimensions>'
                '</field></group>'
                '</definition>'),
            'dim4': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="1">'
                '<dim index="1">$datasource.ann2<strategy mode="CONFIG" />'
                '</dim></dimensions>'
                '</field></group>'
                '</definition>'),
            'dim5': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="1">'
                '<dim index="1"><strategy mode="CONFIG" />'
                '<datasource type="TANGO" name="ann" />'
                '</dim></dimensions>'
                '</field></group>'
                '</definition>'),
            'dim6': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="2">'
                '<dim index="1" value="$datasource.ann" />'
                '<dim index="2" value="123" />'
                '</dimensions>'
                '</field></group>'
                '</definition>'),
            'dim7': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="2" />'
                '</field></group>'
                '</definition>'),
            'dim8': (
                '<definition><group type="NXentry">'
                '<field type="NX_INT8" name="field1">'
                '<datasource type="TANGO" name="tann1c">'
                '<record name="myattr2"/>'
                '<device member="attribute" name="dsf/sd/we"/>'
                '</datasource>'
                '<strategy mode="INIT"/>'
                '<dimensions rank="2">'
                '<dim index="2" value="123" />'
                '</dimensions>'
                '</field></group>'
                '</definition>'),
            'scan': (
                '<definition><group type="NXentry" name="entry1">'
                '<group type="NXinstrument" name="instrument">'
                '<group type="NXdetector" name="detector">'
                '<field units="m" type="NX_FLOAT" name="counter1">'
                '<strategy mode="STEP"/>'
                '<datasource type="CLIENT"><record name="exp_c01"/>'
                '</datasource></field>'
                '<field units="s" type="NX_FLOAT" name="counter2">'
                '<strategy mode="STEP"/><datasource type="CLIENT">'
                '<record name="exp_c02"/></datasource></field>'
                '<field units="" type="NX_FLOAT" name="mca">'
                '<dimensions rank="1"><dim value="2048" index="1"/>'
                '</dimensions><strategy mode="STEP"/>'
                '<datasource type="CLIENT"><record name="p09/mca/exp.02"/>'
                '</datasource></field></group></group></group></definition>'
                ),

            'scan2': (
                '<definition><group type="NXentry" name="entry1">'
                '<group type="NXinstrument" name="instrument">'
                '<group type="NXdetector" name="detector">'
                '<field units="m" type="NX_FLOAT" name="counter1">'
                '<strategy mode="STEP"/>'
                '<datasource name="c01" type="CLIENT">'
                '<record name="exp_c01"/></datasource></field>'
                '<field units="s" type="NX_FLOAT" name="counter2">'
                '<strategy mode="STEP"/>'
                '<datasource type="CLIENT" name="c02">'
                '<record name="exp_c02"/></datasource></field>'
                '<field units="" type="NX_FLOAT" name="mca">'
                '<dimensions rank="1"><dim value="2048" index="1"/>'
                '</dimensions><strategy mode="STEP"/>'
                '<datasource type="CLIENT"  name="mca">'
                '<record name="p09/mca/exp.02"/>'
                '</datasource></field></group></group></group></definition>'
                ),
            'scan3': (
                '<definition><group type="NXentry" name="entry1">'
                '<group type="NXinstrument" name="instrument">'
                '<group type="NXdetector" name="detector">'
                '<field units="m" type="NX_FLOAT" name="counter1">'
                '<strategy mode="STEP"/>'
                '<datasource name="c01" type="CLIENT">'
                '<record name="exp_c01"/></datasource></field>'
                '<field units="s" type="NX_FLOAT" name="counter2">'
                '<strategy mode="INIT"/>'
                '<datasource type="CLIENT" name="c01">'
                '<record name="exp_c01"/></datasource></field>'
                '<field units="" type="NX_FLOAT" name="mca">'
                '<dimensions rank="1"><dim value="2048" index="1"/>'
                '</dimensions><strategy mode="STEP"/>'
                '<datasource type="CLIENT"  name="mca">'
                '<record name="p09/mca/exp.02"/>'
                '</datasource></field></group></group></group></definition>'
                ),

            }

        self.smycps = {
            'smycp': (
                '<definition><group type="NXcollection" name="dddd">'
                '<field name="long">'
                '$datasources.scalar_long<strategy mode="STEP"/></field>'
                '<field name="short">'
                '$datasources.scalar_short<strategy mode="STEP"/></field>'
                '</group></definition>'),
            'smycp2': (
                '<definition><group type="NXcollection" name="dddd">'
                '<field name="long">'
                '$datasources.spectrum_long<strategy mode="INIT"/></field>'
                '<field name="short">'
                '$datasources.spectrum_short<strategy mode="STEP"/></field>'
                '</group></definition>'),
            'smycp3': (
                '<definition><group type="NXcollection" name="dddd">'
                '<field name="long">'
                '$datasources.image_long<strategy mode="FINAL"/></field>'
                '<field name="short">'
                '$datasources.image_short<strategy mode="STEP"/></field>'
                '</group></definition>'),
            'smycpnt1': (
                '<definition><group type="NXcollection" name="ddddnt">'
                '<field name="long">'
                '$datasources.client_long<strategy mode="FINAL"/></field>'
                '<field name="short">'
                '$datasources.client_short<strategy mode="STEP"/></field>'
                '</group></definition>'),
            }

        self.smycps2 = {
            's2mycp': (
                '<definition><group type="NXcollection" name="dddd2">'
                '<field name="long">'
                '$datasources.scalar2_long<strategy mode="STEP"/></field>'
                '<field name="short">'
                '$datasources.scalar2_short<strategy mode="STEP"/></field>'
                '</group></definition>'),
            's2mycp2': (
                '<definition><group type="NXcollection" name="dddd2">'
                '<field name="long">'
                '$datasources.spectrum2_long<strategy mode="STEP"/></field>'
                '<field name="short">'
                '$datasources.spectrum2_short<strategy mode="FINAL"/></field>'
                '</group></definition>'),
            's2mycp3': (
                '<definition><group type="NXcollection" name="dddd2">'
                '<field name="long">'
                '$datasources.image2_long<strategy mode="STEP"/></field>'
                '<field name="short">'
                '$datasources.image2_short<strategy mode="INIT"/></field>'
                '</group></definition>'),
            's2mycpnt1': (
                '<definition><group type="NXcollection" name="dddd2nt">'
                '<field name="long">'
                '$datasources.client2_long<strategy mode="FINAL"/></field>'
                '<field name="short">'
                '$datasources.client2_short<strategy mode="STEP"/></field>'
                '</group></definition>'),
            }

        self.smydss = {
            'scalar_long': (
                '<definition><datasource type="TANGO" name="scalar_long">'
                '<record name="ScalarLong"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_bool': (
                '<definition><datasource type="TANGO" name="scalar_bool">'
                '<record name="ScalarBoolean"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_short': (
                '<definition><datasource type="TANGO" name="scalar_short">'
                '<record name="ScalarShort"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_ushort': (
                '<definition><datasource type="TANGO" name="scalar_ushort">'
                '<record name="ScalarUShort"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_ulong': (
                '<definition><datasource type="TANGO" name="scalar_ulong">'
                '<record name="ScalarULong"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_long64': (
                '<definition><datasource type="TANGO" name="scalar_long64">'
                '<record name="ScalarLong64"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_ulong64': (
                '<definition><datasource type="TANGO" name="scalar_ulong64">'
                '<record name="ScalarULong64"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_float': (
                '<definition><datasource type="TANGO" name="scalar_float">'
                '<record name="ScalarFloat"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_double': (
                '<definition><datasource type="TANGO" name="scalar_double">'
                '<record name="ScalarDouble"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_string': (
                '<definition><datasource type="TANGO" name="scalar_string">'
                '<record name="ScalarString"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_Encoded': (
                '<definition><datasource type="TANGO" name="scalar_encoded">'
                '<record name="ScalarEncoded"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'scalar_uchar': (
                '<definition><datasource type="TANGO" name="scalar_uchar">'
                '<record name="ScalarUChar"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_long': (
                '<definition><datasource type="TANGO" name="spectrum_long">'
                '<record name="SpectrumLong"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_bool': (
                '<definition><datasource type="TANGO" name="spectrum_bool">'
                '<record name="SpectrumBoolean"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_short': (
                '<definition><datasource type="TANGO" name="spectrum_short">'
                '<record name="SpectrumShort"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_ushort': (
                '<definition><datasource type="TANGO" name="spectrum_ushort">'
                '<record name="SpectrumUShort"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_ulong': (
                '<definition><datasource type="TANGO" name="spectrum_ulong">'
                '<record name="SpectrumULong"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_long64': (
                '<definition><datasource type="TANGO" name="spectrum_long64">'
                '<record name="SpectrumLong64"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_ulong64': (
                '<definition><datasource type="TANGO" name="spectrum_ulong64">'
                '<record name="SpectrumULong64"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_float': (
                '<definition><datasource type="TANGO" name="spectrum_float">'
                '<record name="SpectrumFloat"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_double': (
                '<definition><datasource type="TANGO" name="spectrum_double">'
                '<record name="SpectrumDouble"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_string': (
                '<definition><datasource type="TANGO" name="spectrum_string">'
                '<record name="SpectrumString"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_Encoded': (
                '<definition><datasource type="TANGO" name="spectrum_encoded">'
                '<record name="SpectrumEncoded"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'spectrum_uchar': (
                '<definition><datasource type="TANGO" name="spectrum_uchar">'
                '<record name="SpectrumUChar"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'image_long': (
                '<definition><datasource type="TANGO" name="image_long">'
                '<record name="ImageLong"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'image_bool': (
                '<definition><datasource type="TANGO" name="image_bool">'
                '<record name="ImageBoolean"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'image_short': (
                '<definition><datasource type="TANGO" name="image_short">'
                '<record name="ImageShort"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'image_ushort': (
                '<definition><datasource type="TANGO" name="image_ushort">'
                '<record name="ImageUShort"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'image_ulong': (
                '<definition><datasource type="TANGO" name="image_ulong">'
                '<record name="ImageULong"/>'
                '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                '</datasource></definition>'),
            'image_long64':
                ('<definition><datasource type="TANGO" name="image_long64">'
                 '<record name="ImageLong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'image_ulong64':
                ('<definition><datasource type="TANGO" name="image_ulong64">'
                 '<record name="ImageULong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'image_float':
                ('<definition><datasource type="TANGO" name="image_float">'
                 '<record name="ImageFloat"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'image_double':
                ('<definition><datasource type="TANGO" name="image_double">'
                 '<record name="ImageDouble"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'image_string':
                ('<definition><datasource type="TANGO" name="image_string">'
                 '<record name="ImageString"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'image_Encoded':
                ('<definition><datasource type="TANGO" name="image_encoded">'
                 '<record name="ImageEncoded"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'image_uchar':
                ('<definition><datasource type="TANGO" name="image_uchar">'
                 '<record name="ImageUChar"/>'
                 '<device member="attribute" name="ttestp09/testts/t1r228"/>'
                 '</datasource></definition>'),
            'client_long':
                ('<definition><datasource type="CLIENT" name="client_long">'
                 '<record name="ClientLong"/>'
                 '</datasource></definition>'),
            'client_short':
                ('<definition><datasource type="CLIENT" name="client_short">'
                 '<record name="ClientShort"/>'
                 '</datasource></definition>'),
            }

        self.smydss2 = {
            'scalar2_long':
                ('<definition><datasource type="TANGO" name="scalar2_long">'
                 '<record name="ScalarLong"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_bool':
                ('<definition><datasource type="TANGO" name="scalar2_bool">'
                 '<record name="ScalarBoolean"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_short':
                ('<definition><datasource type="TANGO" name="scalar2_short">'
                 '<record name="ScalarShort"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_ushort':
                ('<definition><datasource type="TANGO" name="scalar2_ushort">'
                 '<record name="ScalarUShort"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_ulong':
                ('<definition><datasource type="TANGO" name="scalar2_ulong">'
                 '<record name="ScalarULong"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_long64':
                ('<definition><datasource type="TANGO" name="scalar2_long64">'
                 '<record name="ScalarLong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_ulong64':
                ('<definition><datasource type="TANGO" name="scalar2_ulong64">'
                 '<record name="ScalarULong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_float':
                ('<definition><datasource type="TANGO" name="scalar2_float">'
                 '<record name="ScalarFloat"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_double':
                ('<definition><datasource type="TANGO" name="scalar2_double">'
                 '<record name="ScalarDouble"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_string':
                ('<definition><datasource type="TANGO" name="scalar2_string">'
                 '<record name="ScalarString"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_Encoded':
                ('<definition><datasource type="TANGO" name="scalar2_encoded">'
                 '<record name="ScalarEncoded"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'scalar2_uchar':
                ('<definition><datasource type="TANGO" name="scalar2_uchar">'
                 '<record name="ScalarUChar"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_long':
                ('<definition><datasource type="TANGO" name="spectrum2_long">'
                 '<record name="SpectrumLong"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_bool':
                ('<definition><datasource type="TANGO" name="spectrum2_bool">'
                 '<record name="SpectrumBoolean"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_short':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_short">'
                 '<record name="SpectrumShort"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_ushort':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_ushort">'
                 '<record name="SpectrumUShort"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_ulong':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_ulong">'
                 '<record name="SpectrumULong"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_long64':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_long64">'
                 '<record name="SpectrumLong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_ulong64':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_ulong64">'
                 '<record name="SpectrumULong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_float':
                ('<definition><datasource type="TANGO" name="spectrum2_float">'
                 '<record name="SpectrumFloat"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_double':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_double">'
                 '<record name="SpectrumDouble"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_string':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_string">'
                 '<record name="SpectrumString"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_Encoded':
                ('<definition>'
                 '<datasource type="TANGO" name="spectrum2_encoded">'
                 '<record name="SpectrumEncoded"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'spectrum2_uchar':
                ('<definition><datasource type="TANGO" name="spectrum2_uchar">'
                 '<record name="SpectrumUChar"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_long':
                ('<definition><datasource type="TANGO" name="image2_long">'
                 '<record name="ImageLong"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_bool':
                ('<definition><datasource type="TANGO" name="image2_bool">'
                 '<record name="ImageBoolean"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_short':
                ('<definition><datasource type="TANGO" name="image2_short">'
                 '<record name="ImageShort"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_ushort':
                ('<definition><datasource type="TANGO" name="image2_ushort">'
                 '<record name="ImageUShort"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_ulong':
                ('<definition><datasource type="TANGO" name="image2_ulong">'
                 '<record name="ImageULong"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_long64':
                ('<definition><datasource type="TANGO" name="image2_long64">'
                 '<record name="ImageLong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_ulong64':
                ('<definition><datasource type="TANGO" name="image2_ulong64">'
                 '<record name="ImageULong64"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_float':
                ('<definition><datasource type="TANGO" name="image2_float">'
                 '<record name="ImageFloat"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_double':
                ('<definition><datasource type="TANGO" name="image2_double">'
                 '<record name="ImageDouble"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_string':
                ('<definition><datasource type="TANGO" name="image2_string">'
                 '<record name="ImageString"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_Encoded':
                ('<definition><datasource type="TANGO" name="image2_encoded">'
                 '<record name="ImageEncoded"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'image2_uchar':
                ('<definition><datasource type="TANGO" name="image2_uchar">'
                 '<record name="ImageUChar"/>'
                 '<device member="attribute" name="ttestp09/testts/t2r228"/>'
                 '</datasource></definition>'),
            'client2_long':
                ('<definition><datasource type="CLIENT" name="client2_long">'
                 '<record name="Client2Long"/>'
                 '</datasource></definition>'),
            'client2_short':
                ('<definition><datasource type="CLIENT" name="client2_short">'
                 '<record name="Client2Short"/>'
                 '</datasource></definition>'),
            }

        self.mydss = {
            'nn':
            ('<?xml version=\'1.0\'?><definition><datasource type="TANGO">'
             '</datasource></definition>'),
            'nn2': ('<definition><datasource type="TANGO" name="">'
                    '</datasource></definition>'),
            'ann': ('<definition><datasource type="TANGO" name="ann">'
                    '</datasource></definition>'),
            'ann2': ('<definition><datasource type="CLIENT" name="ann2">'
                     '</datasource></definition>'),
            'ann3': ('<definition><datasource type="DB" name="ann3">'
                     '</datasource></definition>'),
            'ann4': ('<definition><datasource type="PYEVAL" name="ann4">'
                     '</datasource></definition>'),
            'ann5': ('<definition><datasource type="NEW" name="ann5">'
                     '</datasource></definition>'),
            'tann0': ('<definition><datasource type="TANGO" name="tann0">'
                     '<record name="myattr"/>'
                     '<device port="12345" encoding="sfd" hostname="sf" '
                     'member="attribute" name="dsff"/>'
                     '</datasource></definition>'),
            'tann1': ('<definition><datasource type="TANGO" name="tann1">'
                     '<record name="myattr2"/>'
                     '<device port="10000" encoding="sfd" hostname="sfa" '
                     'member="attribute" name="dsf"/>'
                     '</datasource></definition>'),
            'tann1b': ('<definition><datasource type="TANGO" name="tann1b">'
                     '<record name="myattr2"/>'
                     '<device member="attribute" name="dsf"/>'
                     '</datasource></definition>'),
            'tann1c': ('<definition><datasource type="TANGO" name="tann1c">'
                     '<record name="myattr2"/>'
                     '<device member="attribute" name="dsf/sd/we"/>'
                     '</datasource></definition>'),
            'P1M_postrun': (
                '<definition>'
                '<datasource type="PYEVAL" name="P1M_postrun">'
                '<result name="result">'
                'ds.result = "" + ds.P1M_fileDir + "/" + ds.P1M_filePrefix + '
                '"%03i" + ds.P1M_filePostfix + ":1:" + '
                ' str(ds.P1M_fileStartNum)</result>'
                ' $datasources.P1M_fileStartNum'
                ' $datasources.P1M_fileDir'
                ' $datasources.P1M_filePostfix'
                ' $datasources.P1M_filePrefix</datasource>'
                '</definition>'),
            'dbtest': (
                '<definition>'
                '<datasource type="DB" name="dbtest">'
                '<database dbtype="MYSQL"/>'
                '<query format="SPECTRUM">select name for device;</query>'
                '</datasource>'
                '</definition>'),
            'dbds': (
                '<definition>'
                '<datasource type="DB">'
                '<database dbtype="MYSQL">complicated DSN string</database>'
                '<query format="IMAGE">select * from device</query>'
                '<doc>test database datasource</doc>'
                '</datasource>'
                '</definition>'),
            'slt1vgap': (
                '<definition>'
                '<datasource type="CLIENT" name="slt1vgap">'
                '<record name="p02/slt/exp.07"/>'
                '</datasource>'
                '</definition>'
                ),
            }

    ## test starter
    # \brief Common set up
    def setUp(self):
        print "SEED =", self.__seed
        self._wr.setUp()
        self._ms.setUp()
        self._cf.setUp()
        self._pool.setUp()
#        self._ms2.setUp()
        self._simps.setUp()
#        self._simps2.setUp()
#        self._simps3.setUp()
#        self._simps4.setUp()
#        self._simpsoff.add()
        print "\nsetting up..."

    ## test closer
    # \brief Common tear down
    def tearDown(self):
        print "tearing down ..."
#        self._simpsoff.delete()
#        self._simps4.tearDown()
#        self._simps3.tearDown()
#        self._simps2.tearDown()
        self._simps.tearDown()
#        self._ms2.tearDown()
        self._pool.tearDown()
        self._cf.tearDown()
        self._ms.tearDown()
        self._wr.tearDown()

    def dump(self, el):
        self.__dump = {}
        for key in el.keys():
            self.__dump[key] = el[key]

    def compareToDump(self, el, excluded=None):
        exc = set(excluded or [])
        dks = set(self.__dump.keys()) - exc
        eks = set(el.keys()) - exc
        self.assertEqual(dks, eks)
        for key in dks:
            self.assertEqual(self.__dump[key], el[key])

    def compareToDumpJSON(self, el, excluded=None):
        exc = set(excluded or [])
        dks = set(self.__dump.keys()) - exc
        eks = set(el.keys()) - exc
        self.assertEqual(dks, eks)
        for key in dks:
            try:
                w1 = json.loads(self.__dump[key])
                w2 = json.loads(el[key])
            except:
                self.assertEqual(self.__dump[key], el[key])
            else:
                if isinstance(w1, dict):
                    self.myAssertDict(w1, w2)
                else:
                    self.assertEqual(self.__dump[key], el[key])

    def getRandomName(self, maxsize):
        letters = string.lowercase + string.uppercase + string.digits
        size = self.__rnd.randint(1, maxsize)
        return ''.join(self.__rnd.choice(letters) for _ in range(size))

    ## Exception tester
    # \param exception expected exception
    # \param method called method
    # \param args list with method arguments
    # \param kwargs dictionary with method arguments
    def myAssertRaise(self, exception, method, *args, **kwargs):
        err = None
        try:
            error = False
            method(*args, **kwargs)
        except exception, e:
            error = True
            err = e
        self.assertEqual(error, True)
        return err

    def myAssertDict(self, dct, dct2):
        logger.debug('dict %s' % type(dct))
        logger.debug("\n%s\n%s" % (dct, dct2))
        self.assertTrue(isinstance(dct, dict))
        self.assertTrue(isinstance(dct2, dict))
        logger.debug("%s %s" % (len(dct.keys()), len(dct2.keys())))
        self.assertEqual(len(dct.keys()), len(dct2.keys()))
        for k, v in dct.items():
            logger.debug("%s  in %s" % (str(k), str(dct2.keys())))
            self.assertTrue(k in dct2.keys())
            if isinstance(v, dict):
                self.myAssertDict(v, dct2[k])
            else:
                logger.debug("%s , %s" % (str(v), str(dct2[k])))
                self.assertEqual(v, dct2[k])

    ## constructor test
    # \brief It tests default settings
    def test_constructor_keys(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        se = Selector(None)
        self.assertEqual(se.moduleLabel, 'module')
        msp = MacroServerPools(10)
        se = Selector(msp)
        self.assertEqual(se.moduleLabel, 'module')
#        print se.keys()
#        print [rc[0] for rc in self._keys]
        self.assertEqual(sorted(se.keys()),
                         sorted([rc[0] for rc in self._keys])
                         )

        self.assertEqual(se.getPools(), [])
        self.assertEqual(se.getMacroServer(), self._ms.ms.keys()[0])
        db = PyTango.Database()
        db.put_device_property(self._ms.ms.keys()[0],
                               {'PoolNames': self._pool.dp.name()})
        self._ms.dps[self._ms.ms.keys()[0]].Init()
        pools = se.getPools()
        self.assertEqual(len(pools), 1)
        self.assertTrue(isinstance(pools[0], PyTango.DeviceProxy))
        self.assertEqual(pools[0].name(), self._pool.dp.name())
        self.assertEqual(se.getMacroServer(), self._ms.ms.keys()[0])

    ## constructor test
    # \brief It tests default settings
    def test_se_getPool_1to3(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        doors = ["door2testp09/testts/t1r228",
                 "door2testp09/testts/t2r228",
                 "door2testp09/testts/t3r228"]
        msname = "ms2testp09/testts/t1r228"
        try:

            ms2 = TestMacroServerSetUp.TestMacroServerSetUp(
                "MSTESTS1TO3", [msname], doors)
            ms2.setUp()

            msp = MacroServerPools(10)
            db = PyTango.Database()
            se = Selector(msp)
            db.put_device_property(ms2.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            ms2.dps[ms2.ms.keys()[0]].Init()

            for i in range(3):
                ms2.dps[ms2.ms.keys()[0]].DoorList = doors
                self.myAssertRaise(Exception, msp.updateMacroServer,
                                   "sfdsTESTdfdf/sdfsdf/sdffsf")
                self.myAssertRaise(Exception, msp.updateMacroServer, "")
                self.myAssertRaise(Exception, msp.getMacroServer, "")
                self.myAssertRaise(Exception, msp.getPools, "")
                self.myAssertRaise(Exception, se.getMacroServer, "")
                self.myAssertRaise(Exception, se.getPools, "")
                print doors[i]

                se["Door"] = doors[i]
#                msp.updateMacroServer(doors[i])
                print "door",  se["Door"]
                pools = se.getPools()
                self.assertEqual(len(pools), 1)
                self.assertTrue(isinstance(pools[0], PyTango.DeviceProxy))
                self.assertEqual(pools[0].name(), self._pool.dp.name())
                self.assertEqual(msp.getMacroServer(doors[i]),
                                 ms2.ms.keys()[0])
                print "door",  se["Door"]
                self.assertEqual(se.getMacroServer(), ms2.ms.keys()[0])

        finally:
            ms2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_se_getPool_3to3(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        doors = ["door3testp09/testts/t1r228",
                 "door3testp09/testts/t2r228",
                 "door3testp09/testts/t3r228"]
        mss = ["ms3testp09/testts/t1r228",
               "ms3testp09/testts/t2r228",
               "ms3testp09/testts/t3r228"]
        try:

            ms3 = TestMacroServerSetUp.TestMacroServerSetUp(
                "MSTESTS3TO3", mss, doors)
            ms3.setUp()

            msp = MacroServerPools(10)
            db = PyTango.Database()
            se = Selector(msp)
            for j, ms in enumerate(mss):
                db.put_device_property(ms,
                                       {'PoolNames': self._pool.dp.name()})
                ms3.dps[ms].Init()

            for i, ms in enumerate(mss):
                ms3.dps[ms].DoorList = [doors[i]]
#                print "ms", ms, "doors", doors[i]
                self.myAssertRaise(Exception, se.getMacroServer, "")
                self.myAssertRaise(Exception, se.getPools, "")
                se["Door"] = doors[i]
#                msp.updateMacroServer(doors[i])
                print "door",  se["Door"]
                pools = se.getPools()
                self.assertEqual(len(pools), 1)
                self.assertTrue(isinstance(pools[0], PyTango.DeviceProxy))
                self.assertEqual(pools[0].name(), self._pool.dp.name())
                self.assertEqual(msp.getMacroServer(doors[i]), ms)
                print "door",  se["Door"]
                self.assertEqual(se.getMacroServer(), ms)

        finally:
            ms3.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_poolMotors(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        se = Selector(None)
        self.myAssertRaise(Exception, se.poolMotors)
        msp = MacroServerPools(10)
        se = Selector(msp)

        db = PyTango.Database()
        db.put_device_property(self._ms.ms.keys()[0],
                               {'PoolNames': self._pool.dp.name()})
        self._ms.dps[self._ms.ms.keys()[0]].Init()

        pools = se.getPools()

        self.assertEqual(se.poolMotors(), [])

        arr = [
            {"name":"test/ct/01", "controller":"counter_01/Value"},
            {"name":"test/ct/02", "controller":"counter_02/att"},
            {"name":"test/ct/03", "controller":"counter_03/value"},
            {"name":"test/ct/04", "controller":"counter_04/13"},
            {"name":"null", "controller":"counter_04"},
            ]

        arr2 = [
            ["test/mca/01", "mca_01"],
            ["test/mca/02", "mca_02"],
            ["test/sca/03", "my_sca1"],
            ["test/sca/04", "mysca_123"],
            ]

        pool = self._pool.dp
        pool.MotorList = [json.dumps(a) for a in arr]

        dd = se.poolMotors()
        self.assertEqual(dd, [a["name"] for a in arr])

        pool.MotorList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr2]

        dd = se.poolMotors()
        res = [a[0] for a in arr2]
        self.assertEqual(dd, res)

        print se.poolMotors()

        self.assertEqual(len(pools), 1)
        self.assertTrue(isinstance(pools[0], PyTango.DeviceProxy))
        self.assertEqual(pools[0].name(), self._pool.dp.name())
        self.assertEqual(se.getMacroServer(), self._ms.ms.keys()[0])

    ## constructor test
    # \brief It tests default settings
    def test_poolChannels(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        se = Selector(None)
        self.myAssertRaise(Exception, se.poolChannels)
        msp = MacroServerPools(10)
        se = Selector(msp)

        db = PyTango.Database()
        db.put_device_property(self._ms.ms.keys()[0],
                               {'PoolNames': self._pool.dp.name()})
        self._ms.dps[self._ms.ms.keys()[0]].Init()

        pools = se.getPools()

        self.assertEqual(se.poolChannels(), [])

        arr = [
            {"name":"test/ct/01", "controller":"counter_01/Value"},
            {"name":"test/ct/02", "controller":"counter_02/att"},
            {"name":"test/ct/03", "controller":"counter_03/value"},
            {"name":"test/ct/04", "controller":"counter_04/13"},
            {"name":"null", "controller":"counter_04"},
            ]

        arr2 = [
            ["test/mca/01", "mca_01"],
            ["test/mca/02", "mca_02"],
            ["test/sca/03", "my_sca1"],
            ["test/sca/04", "mysca_123"],
            ]

        pool = self._pool.dp
        pool.ExpChannelList = [json.dumps(a) for a in arr]

        dd = se.poolChannels()
        self.assertEqual(dd, [a["name"] for a in arr])

        pool.ExpChannelList = [json.dumps(
                {"name":a[0], "controller":a[1]}) for a in arr2]

        dd = se.poolChannels()
        res = [a[0] for a in arr2]
        self.assertEqual(dd, res)

        print se.poolChannels()

        self.assertEqual(len(pools), 1)
        self.assertTrue(isinstance(pools[0], PyTango.DeviceProxy))
        self.assertEqual(pools[0].name(), self._pool.dp.name())
        self.assertEqual(se.getMacroServer(), self._ms.ms.keys()[0])

    ## updateOrderedChannels test
    def test_resetAutomaticComponents(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)
            dss1 = [self.getRandomName(10) for _ in range(lds1)]

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = bool(self.__rnd.randint(0, 1))
            se["AutomaticComponentGroup"] = json.dumps(cps)

            self.dump(se)

            if i % 2:
                se.resetAutomaticComponents(dss1)

                self.compareToDump(se, ["AutomaticComponentGroup"])

                ndss = json.loads(se["AutomaticComponentGroup"])
                for ds in dss1:
                    self.assertTrue(ds in ndss.keys())
                    self.assertEqual(ndss[ds], False)
            else:
                se.reset()
                self.assertEqual(se["AutomaticComponentGroup"], "{}")

    ## updateOrderedChannels test
    def test_ConfigServer(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            db = PyTango.Database()
            self.assertTrue(se["ConfigDevice"],
                            TangoUtils.getDeviceName(db, "NXSConfigServer"))
            se["ConfigDevice"] = val["ConfigDevice"]
            self.assertTrue(se["ConfigDevice"], val["ConfigDevice"])

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

    #        print "se", se["ConfigDevice"]
            se["ConfigDevice"] = "dfd"
            self.assertTrue(se["ConfigDevice"], "dfd")
            se["ConfigDevice"] = "module"
            self.assertTrue(se["ConfigDevice"], "module")
    #        print "se", se["ConfigDevice"]
            se["ConfigDevice"] = ""
            self.assertTrue(se["ConfigDevice"],
                            TangoUtils.getDeviceName(db, "NXSConfigServer"))
    #        print "se", se["ConfigDevice"]

            se.reset()
            self.assertTrue(se["ConfigDevice"],
                            TangoUtils.getDeviceName(db, "NXSConfigServer"))
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.assertTrue(se["ConfigDevice"], val["ConfigDevice"])

    ## updateOrderedChannels test
    def test_WriterDevice(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            db = PyTango.Database()
            self.assertTrue(se["WriterDevice"],
                            TangoUtils.getDeviceName(db, "NXSDataWriter"))
            se["WriterDevice"] = val["WriterDevice"]
            self.assertTrue(se["WriterDevice"], val["WriterDevice"])

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

    #        print "se", se["WriterDevice"]
            se["WriterDevice"] = "dfd"
            self.assertTrue(se["WriterDevice"], "dfd")
            se["WriterDevice"] = "module"
            self.assertTrue(se["WriterDevice"], "module")
    #        print "se", se["WriterDevice"]
            se["WriterDevice"] = ""
            self.assertTrue(se["WriterDevice"],
                            TangoUtils.getDeviceName(db, "NXSDataWriter"))
    #        print "se", se["WriterDevice"]
            se.reset()
            self.assertTrue(se["WriterDevice"],
                            TangoUtils.getDeviceName(db, "NXSDataWriter"))

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.assertTrue(se["WriterDevice"], val["WriterDevice"])

    def setDoor(self, se, door):
        se["Door"] = door

    ## updateOrderedChannels test
    def test_Door(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        msname = self._ms.ms.keys()[0]
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            db = PyTango.Database()
            self.assertTrue(se["Door"],
                            TangoUtils.getDeviceName(db, "Door"))
            se["Door"] = val["Door"]
            self.assertEqual(se.getMacroServer(), msname)
            self.assertTrue(se["Door"], val["Door"])
            self.assertEqual(se.getMacroServer(), msname)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()

            self.myAssertRaise(Exception, self.setDoor, se, "dfd")
            self.assertTrue(se["Door"], "dfd")
            self.myAssertRaise(Exception, se.getMacroServer)
    #        se["Door"] = "module"
            self.myAssertRaise(Exception, self.setDoor, se, "module")
            self.myAssertRaise(Exception, se.getMacroServer)
            self.assertTrue(se["Door"], "module")
            self.myAssertRaise(Exception, se.getMacroServer)
    #        print "se", se["Door"]
    #        self.assertEqual(se.getMacroServer(), msname)
            se["Door"] = ""
            door = TangoUtils.getDeviceName(db, "Door")
            ms = MSUtils.getMacroServer(db, door)
            self.assertEqual(se.getMacroServer(), ms)
            self.assertTrue(se["Door"],
                            TangoUtils.getDeviceName(db, "Door"))
    #        print "se", se["Door"]
            self.assertEqual(se.getMacroServer(), ms)
            se.reset()
            self.assertEqual(se.getMacroServer(), ms)
            self.assertTrue(se["Door"],
                            TangoUtils.getDeviceName(db, "Door"))
    #        print "se", se["Door"]
            self.assertEqual(se.getMacroServer(), ms)

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.assertEqual(se.getMacroServer(), msname)
            self.assertTrue(se["Door"], val["Door"])
            self.assertEqual(se.getMacroServer(), msname)

    ## deselect test
    def test_MntGrp(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            self.assertEqual(se["MntGrp"], self.__defaultmntgrp)
            mg = self.getRandomName(10)
            se["MntGrp"] = mg
            self.assertEqual(se["MntGrp"], mg)

            se["MntGrp"] = ""
            self.assertEqual(se["MntGrp"], self.__defaultmntgrp)
            mg = self.getRandomName(10)
            se["MntGrp"] = mg
            self.assertEqual(se["MntGrp"], mg)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            se.reset()
            self.assertEqual(se["MntGrp"], self.__defaultmntgrp)

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.assertEqual(se["MntGrp"], mg)

    ## deselect test
    def test_TimeZone(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            self.assertEqual(se["TimeZone"], self.__defaultzone)
            mg = self.getRandomName(10)
            se["TimeZone"] = mg
            self.assertEqual(se["TimeZone"], mg)
            se["TimeZone"] = ""
            self.assertEqual(se["TimeZone"], self.__defaultzone)
            mg = self.getRandomName(10)
            se["TimeZone"] = mg
            self.assertEqual(se["TimeZone"], mg)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            se.reset()
            self.assertEqual(se["TimeZone"], self.__defaultzone)

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.assertEqual(se["TimeZone"], mg)

    ## deselect test
    def test_setConfigInstance(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        db = PyTango.Database()

        inst = se.setConfigInstance()
        icf = TangoUtils.getDeviceName(db, "NXSConfigServer")
        self.assertTrue(isinstance(inst, PyTango.DeviceProxy))
        self.assertEqual(inst.name(), icf)
        dev_info = inst.info()
        self.assertEqual(dev_info.dev_class, "NXSConfigServer")

        se["ConfigDevice"] = val["ConfigDevice"]
        inst = se.setConfigInstance()
        self.assertTrue(isinstance(inst, PyTango.DeviceProxy))
        self.assertEqual(inst.name(), val["ConfigDevice"])
        dev_info = inst.info()
        self.assertEqual(dev_info.dev_class, "NXSConfigServer")

        se["ConfigDevice"] = "sdfsfdsf,./wrwrwe/wer"
        self.myAssertRaise(Exception, se.setConfigInstance)

        se["ConfigDevice"] = val["WriterDevice"]
        self.myAssertRaise(Exception, se.setConfigInstance)

        se["ConfigDevice"] = val["Door"]
        self.myAssertRaise(Exception, se.setConfigInstance)

        se.reset()
        self.assertTrue(isinstance(inst, PyTango.DeviceProxy))
        self.assertEqual(inst.name(), icf)
        dev_info = inst.info()
        self.assertEqual(dev_info.dev_class, "NXSConfigServer")

        se["ConfigDevice"] = 'module'
        if DB_AVAILABLE:
            print "DB AVAILABLE:", DB_AVAILABLE
            inst = se.setConfigInstance()
            self.assertTrue(isinstance(inst, XMLConfigurator))

        se.reset()
        inst = se.setConfigInstance()
        self.assertTrue(isinstance(inst, PyTango.DeviceProxy))
        self.assertEqual(inst.name(), icf)
        dev_info = inst.info()
        self.assertEqual(dev_info.dev_class, "NXSConfigServer")

    def test_configCommand(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        db = PyTango.Database()

        se["ConfigDevice"] = val["ConfigDevice"]

        arg = [
            ["AvailableComponents", None],
            ["AvailableDataSources", None],
            ["AvailableSelections", None],
            ["MandatoryComponents", None],
            ["availableComponents", None],
            ["availableDataSources", None],
            ["availableSelections", None],
            ["mandatoryComponents", None],
            ]

        for ar in arg:
            self._cf.dp.Init()
            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.mycps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.mydss)])
            self._cf.dp.SetCommandVariable(["SELDICT", json.dumps(self.mysel)])
            mcp = self.__rnd.sample(
                self.mycps.keys(),
                self.__rnd.randint(0, len(self.mycps.keys())))
            self._cf.dp.SetCommandVariable(["MCPLIST", json.dumps(mcp)])
            se = Selector(msp)
            res = se.configCommand(ar[0])
            print self._cf.dp.GetCommandVariable("COMMANDS")
            self.assertEqual(
                [c.lower() for c in
                 json.loads(self._cf.dp.GetCommandVariable("COMMANDS"))],
                [ar[0].lower()])
            self.assertEqual(
                json.loads(self._cf.dp.GetCommandVariable("VARS")),
                [ar[1]])
            inst = se.setConfigInstance()
            self.assertEqual(res, inst.command_inout(ar[0]))

    def test_configCommand_arg(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        db = PyTango.Database()

        se["ConfigDevice"] = val["ConfigDevice"]
        for i in range(5):
            arg2 = [
                ["Components", self.__rnd.sample(
                            self.mycps.keys(),
                            self.__rnd.randint(0, len(self.mycps.keys())))],
                ["InstantiatedComponents", self.__rnd.sample(
                            self.mycps.keys(),
                            self.__rnd.randint(0, len(self.mycps.keys())))],
                ["CreateConfiguration", self.__rnd.sample(
                            self.mycps.keys(),
                            self.__rnd.randint(0, len(self.mycps.keys())))],
                ["DataSources", self.__rnd.sample(
                            self.mydss.keys(),
                            self.__rnd.randint(0, len(self.mydss.keys())))],
                ["Selections", self.__rnd.sample(
                            self.mysel.keys(),
                            self.__rnd.randint(0, len(self.mysel.keys())))],
                ["StoreSelection", self.__rnd.sample(self.mysel.keys(), 1)[0]],
                ["StoreComponent", self.__rnd.sample(self.mycps.keys(), 1)[0]],
                ["StoreDataSource",
                 self.__rnd.sample(self.mydss.keys(), 1)[0]],
                ["components", self.__rnd.sample(
                            self.mycps.keys(),
                            self.__rnd.randint(0, len(self.mycps.keys())))],
                ["instantiatedComponents", self.__rnd.sample(
                            self.mycps.keys(),
                            self.__rnd.randint(0, len(self.mycps.keys())))],
                ["createConfiguration", self.__rnd.sample(
                            self.mycps.keys(),
                            self.__rnd.randint(0, len(self.mycps.keys())))],
                ["dataSources", self.__rnd.sample(
                            self.mydss.keys(),
                            self.__rnd.randint(0, len(self.mydss.keys())))],
                ["selections", self.__rnd.sample(
                            self.mysel.keys(),
                            self.__rnd.randint(0, len(self.mysel.keys())))],
                ["storeSelection", self.__rnd.sample(self.mysel.keys(), 1)[0]],
                ["storeComponent", self.__rnd.sample(self.mycps.keys(), 1)[0]],
                ["storeDataSource",
                 self.__rnd.sample(self.mydss.keys(), 1)[0]],
               ]
            for ar in arg2:
                self._cf.dp.Init()
                self._cf.dp.SetCommandVariable(
                    ["CPDICT", json.dumps(self.mycps)])
                self._cf.dp.SetCommandVariable(
                    ["DSDICT", json.dumps(self.mydss)])
                self._cf.dp.SetCommandVariable(
                    ["SELDICT", json.dumps(self.mysel)])
                se = Selector(msp)
#                print "COM", ar[0]
#                print "VAR", ar[1]
                res = se.configCommand(ar[0], ar[1])
                print self._cf.dp.GetCommandVariable("COMMANDS")
                self.assertEqual(
                    [c.lower() for c in
                     json.loads(self._cf.dp.GetCommandVariable("COMMANDS"))],
                    [ar[0].lower()])
                self.assertEqual(
                    json.loads(self._cf.dp.GetCommandVariable("VARS")),
                    [ar[1]])
                inst = se.setConfigInstance()
                self.assertEqual(res, inst.command_inout(ar[0], ar[1]))

    def test_configCommand_module(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        db = PyTango.Database()

        if DB_AVAILABLE:

            arg = [
                ["availableComponents", None],
                ["availableDataSources", None],
                ["availableSelections", None],
                ["mandatoryComponents", None],
                ]

            for ar in arg:
                se = Selector(msp)
                se["ConfigDevice"] = 'module'
                res = se.configCommand(ar[0])
                inst = se.setConfigInstance()
                self.assertEqual(res, getattr(inst, ar[0])())

    def test_configCommand_arg_module(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        db = PyTango.Database()

        se["ConfigDevice"] = 'module'
        inst = se.setConfigInstance()
        cps = inst.availableComponents() or []
        dss = inst.availableDataSources() or []
        sls = inst.availableSelections() or []
        print "CPS !!!!", cps
        print "DSS !!!!", dss

        for i in range(5):
            arg2 = [
                ["components", self.__rnd.sample(
                            cps,
                            self.__rnd.randint(0, len(cps)))],
                ["instantiatedComponents", self.__rnd.sample(
                            cps,
                            self.__rnd.randint(0, len(cps)))],
                ["createConfiguration", self.__rnd.sample(
                            cps,
                            self.__rnd.randint(0, len(cps)))],
                ["dataSources", self.__rnd.sample(
                            dss,
                            self.__rnd.randint(0, len(dss)))],
                ["selections", self.__rnd.sample(
                            sls,
                            self.__rnd.randint(0, len(sls)))],
               ]

            for ar in arg2:
                se = Selector(msp)
                se["ConfigDevice"] = 'module'
                res = se.configCommand(ar[0], ar[1])
                self.assertEqual(res, getattr(inst, ar[0])(ar[1]))

    ## updateOrderedChannels test
    def test_AutomaticDataSources(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            pool = self._pool.dp
            pool.MotorList = []
            se["AutomaticDataSources"] = json.dumps([])
            self._ms.dps[self._ms.ms.keys()[0]].Init()

            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)
            lds2 = self.__rnd.randint(1, 40)
            lds3 = self.__rnd.randint(1, 40)
            dss1 = [self.getRandomName(10) for _ in range(lds1)]
            dss2 = [self.getRandomName(10) for _ in range(lds2)]
            dss3 = [self.getRandomName(10) for _ in range(lds3)]

            se["AutomaticDataSources"] = json.dumps(
                list(set(dss1) | set(dss2)))
            self.dump(se)

            ads = se["AutomaticDataSources"]

            self.compareToDump(se, ["AutomaticDataSources"])

            self.assertEqual(set(list(set(dss2) | set(dss1))),
                             set(json.loads(ads)))

            mnames = list(set(dss3) | set(dss2))
            pool = self._pool.dp
            pool.MotorList = [json.dumps(
                    {"name":mn, "controller":("ctrl" + mn)}) for mn in mnames]

            ads = json.loads(se["AutomaticDataSources"])

            self.assertEqual(set(list(set(dss3) | set(dss2) | set(dss1))),
                             set(ads))

            self.compareToDump(se, ["AutomaticDataSources"])

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    if k not in ["AutomaticDataSources"]:
                        try:
                            self.assertEqual(
                                json.loads(se[k]),
                                env["new"]["NeXusConfiguration"][k])
                        except:
                            self.assertEqual(
                                se[k],
                                env["new"]["NeXusConfiguration"][k])
                    else:
                        self.assertEqual(
                            sorted(json.loads(se["AutomaticDataSources"])),
                            sorted(env["new"]["NeXusConfiguration"][k]))
            se.reset()
            ads = json.loads(se["AutomaticDataSources"])
            self.assertEqual(set(mnames), set(ads))

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            ads = json.loads(se["AutomaticDataSources"])
            self.assertEqual(set(list(set(dss3) | set(dss2) | set(dss1))),
                             set(ads))
            self.compareToDump(se, ["AutomaticDataSources"])

    ## updateOrderedChannels test
    def test_OrderedChannels(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["OrderedChannels"] = json.dumps([])
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            pool = self._pool.dp
            pool.ExpChannelList = []
            self._ms.dps[self._ms.ms.keys()[0]].Init()

            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)
            lds2 = self.__rnd.randint(1, 40)
            lds3 = self.__rnd.randint(1, 40)
            dss1 = [self.getRandomName(10) for _ in range(lds1)]
            dss2 = [self.getRandomName(10) for _ in range(lds2)]
            dss3 = [self.getRandomName(10) for _ in range(lds3)]

            dss = []
            dss.extend(dss2)
            for ds in dss1:
                if ds not in dss:
                    dss.append(ds)
            pchs = []
            pchs.extend(dss2)
            for ds in dss3:
                if ds not in pchs:
                    pchs.append(ds)
            pchs = sorted(set(pchs))

            pool = self._pool.dp
            pool.ExpChannelList = [json.dumps(
                    {"name":mn, "controller":("ctrl" + mn)}) for mn in pchs]

            se["OrderedChannels"] = json.dumps(dss)
            self.dump(se)

            ads = se["OrderedChannels"]
            print "OCS:", ads

            self.compareToDumpJSON(se, ["OrderedChannels"])

            ndss = json.loads(se["OrderedChannels"])
            odss = []
            odss.extend(dss2)
            for ds in dss3:
                if ds not in odss:
                    odss.append(ds)

            self.assertEqual(ndss[:len(dss2)], odss[:len(dss2)])
            self.assertEqual(set(ndss), set(odss))

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            se.reset()
            ndss = json.loads(se["OrderedChannels"])
            self.assertEqual(ndss, sorted(pchs))

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            ads = se["OrderedChannels"]
            print "OCS:", ads

            self.compareToDumpJSON(se, ["OrderedChannels"])

            ndss = json.loads(se["OrderedChannels"])
            odss = []
            odss.extend(dss2)
            for ds in dss3:
                if ds not in odss:
                    odss.append(ds)

            self.assertEqual(ndss[:len(dss2)], odss[:len(dss2)])
            self.assertEqual(set(ndss), set(odss))

    ## ComponentGroup test
    def test_ComponentGroup(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["OrderedChannels"] = json.dumps([])
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            pool = self._pool.dp
            pool.ExpChannelList = []
            self._ms.dps[self._ms.ms.keys()[0]].Init()

            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            cps = {}
            dss = {}
            lcp = self.__rnd.randint(1, 40)
            lds = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = bool(self.__rnd.randint(0, 1))
            for i in range(lds):
                dss[self.getRandomName(10)] = bool(self.__rnd.randint(0, 1))
            ccps = self.__rnd.sample(cps, self.__rnd.randint(
                    1, len(cps.keys())))
            for cp in ccps:
                dss[cp] = bool(self.__rnd.randint(0, 1))
            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["ComponentGroup"] = json.dumps(cps)
            se["DataSourceGroup"] = json.dumps(dss)
            ndss = json.loads(se["DataSourceGroup"])
            common = set(cps) & set(dss)
            self.dump(se)

            ncps = json.loads(se["ComponentGroup"])
            ndss = json.loads(se["DataSourceGroup"])

            self.assertEqual(len(cps), len(ncps) + len(common))
            for key in cps.keys():
                if key not in common:
                    self.assertTrue(key in ncps.keys())
                    self.assertEqual(ncps[key], cps[key])
            self.compareToDumpJSON(se, ["ComponentGroup"])

            mydict = {}
            nenv = {
                "Components": self.__rnd.sample(
                    cps, self.__rnd.randint(1, len(cps))),
                "AutomaticComponents": self.__rnd.sample(
                    cps, self.__rnd.randint(1, len(cps))),
                "DataSources": self.__rnd.sample(
                    cps, self.__rnd.randint(1, len(cps)))
                }

            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 8 - 2:
                    se.exportEnv(cmddata=nenv)
                elif (i / 2) % 8 - 4:
                    se.exportEnv(mydict, cmddata=nenv)
                elif (i / 2) % 8 - 6:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            if i % 2:
                se.deselect()
                self.compareToDumpJSON(se, ["ComponentGroup",
                                            "DataSourceGroup"])
                ncps = json.loads(se["ComponentGroup"])
                ndss = json.loads(se["DataSourceGroup"])
                for key in cps.keys():
                    if key not in common:
                        self.assertTrue(key in ncps.keys())
                        self.assertEqual(ncps[key], False)
                for key in dss.keys():
                    if key not in common:
                        self.assertTrue(key in dss.keys())
                        self.assertEqual(ndss[key], False)
            else:
                se.reset()
                for key, vl in self._keys:
                    self.assertTrue(key in se.keys())
                    if key not in val:
                        self.assertEqual(se[key], vl)
                self.assertEqual(se["MntGrp"], val["MntGrp"])
                self.assertTrue(se["Door"],
                                TangoUtils.getDeviceName(db, "Door"))
                self.assertTrue(
                    se["ConfigDevice"],
                    TangoUtils.getDeviceName(db, "NXSConfigServer"))
                self.assertTrue(
                    se["WriterDevice"],
                    TangoUtils.getDeviceName(db, "NXSDataWriter"))

            mydata = {}
            mycmd = {}
            if (i / 2) % 2:
                if (i / 2) % 8:
                    se.set(mydict)
                elif (i / 2) % 8 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
                elif (i / 2) % 8 - 4:
                    se.importEnv(data=mydata)
                    se.set(mydata)
                    se.importEnv(names=nenv.keys(), data=mycmd)
                    self.assertEqual(mycmd, nenv)
                elif (i / 2) % 8 - 6:
                    se.importEnv(data=mydata)
                    se.set(mydata)
                    se.importEnv(names=nenv.keys(), data=mycmd)
                    self.assertEqual(mycmd, nenv)

            else:
                se.importEnv()

            ncps = json.loads(se["ComponentGroup"])
            ndss = json.loads(se["DataSourceGroup"])

            self.assertEqual(len(cps), len(ncps) + len(common))
            for key in cps.keys():
                if key not in common:
                    self.assertTrue(key in ncps.keys())
                    self.assertEqual(ncps[key], cps[key])
            self.compareToDumpJSON(se, ["ComponentGroup"])

    ## DataSourceGroup test
    def test_DataSourceGroup(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp',
               "OrderedChannels": "[]",
               "DataSourceGroup": "{}"}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            pool = self._pool.dp
            pool.ExpChannelList = []
            self._ms.dps[self._ms.ms.keys()[0]].Init()

            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            dss = {}
            lall = self.__rnd.randint(1, 40)
            adss = [self.getRandomName(10) for _ in range(lall)]

            dssn = set(self.__rnd.sample(adss, self.__rnd.randint(1, lall)))
            chs = set(self.__rnd.sample(adss, self.__rnd.randint(1, lall)))
            cdss = set(self.__rnd.sample(adss, self.__rnd.randint(1, lall)))

            for ds in dssn:
                dss[ds] = bool(self.__rnd.randint(0, 1))
            se["DataSourceGroup"] = json.dumps(dss)

            pool = self._pool.dp
            pool.ExpChannelList = [json.dumps(
                    {"name":mn, "controller":("ctrl" + mn)}) for mn in chs]

            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(
                        {key: self.smydss["scalar_long"] for key in cdss}
                        )])
            self.dump(se)

            ndss = json.loads(se["DataSourceGroup"])
            existing = set(dssn) & (set(chs) | set(cdss))
            print "existing", existing
            for key, value in ndss.items():
                if key in existing:
                    self.assertEqual(ndss[key], dss[key])
                else:
                    self.assertTrue(key in chs)
                    self.assertTrue(not value)
            self.compareToDumpJSON(se, ["DataSourceGroup"])

            mydict = {}
            nenv = {
                "Components": self.__rnd.sample(
                    adss, self.__rnd.randint(1, len(adss))),
                "AutomaticComponents": self.__rnd.sample(
                    adss, self.__rnd.randint(1, len(adss))),
                "DataSources": self.__rnd.sample(
                    adss, self.__rnd.randint(1, len(adss)))
                }

            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 8 - 2:
                    se.exportEnv(cmddata=nenv)
                elif (i / 2) % 8 - 4:
                    se.exportEnv(mydict, cmddata=nenv)
                elif (i / 2) % 8 - 6:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            if i % 2:
                se.deselect()
                ndss = json.loads(se["DataSourceGroup"])
                self.compareToDumpJSON(se, ["DataSourceGroup"])
                if key in existing:
                    self.assertEqual(ndss[key], False)
                else:
                    self.assertTrue(key in chs)
                    self.assertTrue(not value)
            else:
                se.reset()
                for key, vl in self._keys:
                    self.assertTrue(key in se.keys())
                    if key not in val:
                        self.assertEqual(se[key], vl)
                ndss = json.loads(se["DataSourceGroup"])
                self.assertEqual(sorted(ndss.keys()), sorted(chs))
                for mn in chs:
                    self.assertEqual(ndss[mn], False)
                och = json.loads(se["OrderedChannels"])
                self.assertEqual(och, sorted(chs))
                self.assertEqual(se["MntGrp"], val["MntGrp"])
                self.assertTrue(se["Door"],
                                TangoUtils.getDeviceName(db, "Door"))
                self.assertTrue(
                    se["ConfigDevice"],
                    TangoUtils.getDeviceName(db, "NXSConfigServer"))
                self.assertTrue(
                    se["WriterDevice"],
                    TangoUtils.getDeviceName(db, "NXSDataWriter"))

            mydata = {}
            mycmd = {}
            if (i / 2) % 2:
                if (i / 2) % 8:
                    se.set(mydict)
                elif (i / 2) % 8 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
                elif (i / 2) % 8 - 4:
                    se.importEnv(data=mydata)
                    se.set(mydata)
                    se.importEnv(names=nenv.keys(), data=mycmd)
                    self.assertEqual(mycmd, nenv)
                elif (i / 2) % 8 - 6:
                    se.importEnv(data=mydata)
                    se.set(mydata)
                    se.importEnv(names=nenv.keys(), data=mycmd)
                    self.assertEqual(mycmd, nenv)

            else:
                se.importEnv()

            ndss = json.loads(se["DataSourceGroup"])
            existing = set(dssn) & (set(chs) | set(cdss))
            print "existing", existing
            for key, value in ndss.items():
                if key in existing:
                    self.assertEqual(ndss[key], dss[key])
                else:
                    self.assertTrue(key in chs)
                    self.assertTrue(not value)
            self.compareToDumpJSON(se, ["DataSourceGroup"])

    ## updateOrderedChannels test
    def test_AutomaticComponentGroup(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = bool(self.__rnd.randint(0, 1))
            se["AutomaticComponentGroup"] = json.dumps(cps)

            self.dump(se)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()

            self.compareToDump(se, ["AutomaticComponentGroup"])
            ndss = json.loads(se["AutomaticComponentGroup"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            se.reset()
            self.assertEqual(se["AutomaticComponentGroup"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["AutomaticComponentGroup"])
            ndss = json.loads(se["AutomaticComponentGroup"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## dataRecord test
    def test_DataRecord(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = self.getRandomName(
                    self.__rnd.randint(1, 40))
            se["DataRecord"] = json.dumps(cps)

            self.dump(se)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["DataRecord"])

            ndss = json.loads(se["DataRecord"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])
            se.reset()
            self.assertEqual(se["DataRecord"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            self.compareToDump(se, ["DataRecord"])

            ndss = json.loads(se["DataRecord"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## labels test
    def test_Labels(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = self.getRandomName(
                    self.__rnd.randint(1, 40))
            se["Labels"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["Labels"])

            ndss = json.loads(se["Labels"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])
            se.reset()
            self.assertEqual(se["Labels"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            self.compareToDump(se, ["Labels"])

            ndss = json.loads(se["Labels"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## labelpaths test
    def test_LabelPaths(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = self.getRandomName(
                    self.__rnd.randint(1, 40))
            se["LabelPaths"] = json.dumps(cps)

            self.dump(se)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["LabelPaths"])

            ndss = json.loads(se["LabelPaths"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])
            se.reset()
            self.assertEqual(se["LabelPaths"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            self.compareToDump(se, ["LabelPaths"])

            ndss = json.loads(se["LabelPaths"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## labellinks test
    def test_LabelLinks(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = bool(self.__rnd.randint(0, 1))
            se["LabelLinks"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["LabelLinks"])

            ndss = json.loads(se["LabelLinks"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])
            se.reset()
            self.assertEqual(se["LabelLinks"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["LabelLinks"])

            ndss = json.loads(se["LabelLinks"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## labeltypes test
    def test_LabelTypes(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = self.getRandomName(
                    self.__rnd.randint(1, 40))
            se["LabelTypes"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["LabelTypes"])

            ndss = json.loads(se["LabelTypes"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])
            se.reset()

            self.assertEqual(se["LabelTypes"], "{}")
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            self.compareToDump(se, ["LabelTypes"])

            ndss = json.loads(se["LabelTypes"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## labelshapes test
    def test_LabelShapes(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                dim = self.__rnd.randint(0, 3)
                cps[self.getRandomName(10)] = [
                    self.__rnd.randint(1, 1000) for _ in range(dim)]
            se["LabelShapes"] = json.dumps(cps)

            self.dump(se)

            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["LabelShapes"])

            ndss = json.loads(se["LabelShapes"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

            se.reset()
            self.assertEqual(se["LabelShapes"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            ndss = json.loads(se["LabelShapes"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## configvariables test
    def test_ConfigVariables(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            for i in range(lcp):
                cps[self.getRandomName(10)] = self.getRandomName(
                    self.__rnd.randint(1, 40))
            se["ConfigVariables"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["ConfigVariables"])

            ndss = json.loads(se["ConfigVariables"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])
            se.reset()
            self.assertEqual(se["ConfigVariables"], "{}")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            ndss = json.loads(se["ConfigVariables"])
            for ds in cps.keys():
                self.assertTrue(ds in ndss.keys())
                self.assertEqual(ndss[ds], cps[ds])

    ## timers test
    def test_Timer(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            lcp = self.__rnd.randint(1, 40)
            cps = [self.getRandomName(10) for _ in range(lcp)]
            se["Timer"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["Timer"])

            ndss = json.loads(se["Timer"])
            self.assertEqual(ndss, cps)
            se.reset()
            self.assertEqual(se["Timer"], "[]")
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            self.compareToDump(se, ["Timer"])
            ndss = json.loads(se["Timer"])
            self.assertEqual(ndss, cps)

    ## InitDataSources test
    def test_InitDataSources(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = {}
            lcp = self.__rnd.randint(1, 40)
            cps = [self.getRandomName(10) for _ in range(lcp)]
            se["InitDataSources"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["InitDataSources"])
            ndss = json.loads(se["InitDataSources"])
            self.assertEqual(ndss, cps)

            se.reset()
            self.assertEqual(se["InitDataSources"], "[]")
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["InitDataSources"])
            ndss = json.loads(se["InitDataSources"])
            self.assertEqual(ndss, cps)

    ## OptionalComponents test
    def test_OptionalComponents(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            lcp = self.__rnd.randint(1, 40)
            cps = [self.getRandomName(10) for _ in range(lcp)]
            se["OptionalComponents"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["OptionalComponents"])
            ndss = json.loads(se["OptionalComponents"])
            self.assertEqual(ndss, cps)

            se.reset()
            self.assertEqual(se["OptionalComponents"], "[]")
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["OptionalComponents"])
            ndss = json.loads(se["OptionalComponents"])
            self.assertEqual(ndss, cps)

    ## HiddenElements test
    def test_HiddenElements(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            lcp = self.__rnd.randint(1, 40)
            cps = [self.getRandomName(10) for _ in range(lcp)]
            se["HiddenElements"] = json.dumps(cps)

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["HiddenElements"])
            ndss = json.loads(se["HiddenElements"])
            self.assertEqual(ndss, cps)

            se.reset()
            self.assertEqual(se["HiddenElements"], "[]")

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["HiddenElements"])
            ndss = json.loads(se["HiddenElements"])
            self.assertEqual(ndss, cps)

    ## DynamicPath test
    def test_DynamicPath(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            lcp = self.__rnd.randint(1, 40)
            cps = self.getRandomName(10)
            se["DynamicPath"] = cps

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["DynamicPath"])
            self.assertEqual(se["DynamicPath"], cps)

            se.reset()
            self.assertEqual(se["DynamicPath"],
                             self.__defaultpath)

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()
            self.compareToDump(se, ["DynamicPath"])
            self.assertEqual(se["DynamicPath"], cps)

    ## AppendEntry test
    def test_AppendEntry(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = bool(self.__rnd.randint(0, 1))
            se["AppendEntry"] = cps

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["AppendEntry"])
            self.assertEqual(se["AppendEntry"], cps)

            se.reset()
            self.assertEqual(se["AppendEntry"], False)

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["AppendEntry"])
            self.assertEqual(se["AppendEntry"], cps)

    ## ComponentsFromMntGrp test
    def test_ComponentsFromMntGrp(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = bool(self.__rnd.randint(0, 1))
            se["ComponentsFromMntGrp"] = cps

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["ComponentsFromMntGrp"])
            self.assertEqual(se["ComponentsFromMntGrp"], cps)

            se.reset()
            self.assertEqual(se["ComponentsFromMntGrp"], False)

            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["ComponentsFromMntGrp"])
            self.assertEqual(se["ComponentsFromMntGrp"], cps)

    ## DynamicComponents test
    def test_DynamicComponents(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = bool(self.__rnd.randint(0, 1))
            se["DynamicComponents"] = cps

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["DynamicComponents"])
            self.assertEqual(se["DynamicComponents"], cps)

            se.reset()
            self.assertEqual(se["DynamicComponents"], True)
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["DynamicComponents"])
            self.assertEqual(se["DynamicComponents"], cps)

    ## DynamicLinks test
    def test_DynamicLinks(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        for i in range(20):
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            self.assertEqual(len(se.keys()), len(self._keys))
            for key, vl in self._keys:
                self.assertTrue(key in se.keys())
                if key not in val:
                    self.assertEqual(se[key], vl)
                else:
                    self.assertEqual(se[key], val[key])

            lds1 = self.__rnd.randint(1, 40)

            cps = bool(self.__rnd.randint(0, 1))
            se["DynamicLinks"] = cps

            self.dump(se)
            mydict = {}
            if (i / 2) % 2:
                mydict = se.get()
                if (i / 2) % 4 - 2:
                    se.exportEnv(mydict)
            else:
                se.exportEnv()
                env = pickle.loads(
                    self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
                for k in se.keys():
                    try:
                        self.assertEqual(
                            json.loads(se[k]),
                            env["new"]["NeXusConfiguration"][k])
                    except:
                        self.assertEqual(
                            se[k],
                            env["new"]["NeXusConfiguration"][k])

            self.compareToDump(se, ["DynamicLinks"])
            self.assertEqual(se["DynamicLinks"], cps)

            se.reset()
            self.assertEqual(se["DynamicLinks"], True)
            mydata = {}
            if (i / 2) % 2:
                if (i / 2) % 4:
                    se.set(mydict)
                elif (i / 2) % 4 - 2:
                    se.importEnv(data=mydata)
                    se.set(mydata)
            else:
                se.importEnv()

            self.compareToDump(se, ["DynamicLinks"])
            self.assertEqual(se["DynamicLinks"], cps)

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_simple(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        self.myAssertRaise(Exception, se.updateAutomaticComponents,
                           None)
        res = se.updateAutomaticComponents(channelerrors)
        self.assertEqual(res, '{}')
        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ['AvailableComponents', 'AvailableDataSources',
             'AvailableComponents'])
        self.assertEqual(json.loads(
                self._cf.dp.GetCommandVariable("VARS")), [None, None, None])

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_withcf(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = []
        componentgroup = {}

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.mycps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.mydss)])

        res = se.updateAutomaticComponents(channelerrors)

        self.assertEqual(res, '{}')
        self.assertEqual(componentgroup, {})
        self.assertEqual(channelerrors, [])
        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ["AvailableComponents", "AvailableDataSources",
             "AvailableComponents"])
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("VARS")),
            [None, None, None])
#        print self._cf.dp.availableComponents()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_withcf_cps(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = ["mycp"]
        componentgroup = {"mycp": False}

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.mycps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.mydss)])

        se["AutomaticDataSources"] = json.dumps(poolchannels)
        se["AutomaticComponentGroup"] = json.dumps(componentgroup)
        res = se.updateAutomaticComponents(channelerrors)
        self.myAssertDict(json.loads(res), {"mycp": True})
        self.assertEqual(channelerrors, [])

        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ["AvailableComponents", "AvailableDataSources",
             "AvailableComponents", "Components"])
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("VARS")),
            [None, None, None, ['mycp']])
#        print self._cf.dp.availableComponents()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_withcf_nocps(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = ["mycp"]
        componentgroup = {}

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.mycps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.mydss)])

        se["AutomaticDataSources"] = json.dumps(poolchannels)
        se["AutomaticComponentGroup"] = json.dumps(componentgroup)
        res = se.updateAutomaticComponents(channelerrors)

        self.myAssertDict(json.loads(res), {})
        self.assertEqual(channelerrors, [])

        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ["AvailableComponents", "AvailableDataSources",
             "AvailableComponents"])
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("VARS")),
            [None, None, None])

#        print self._cf.dp.availableComponents()
    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_withcf_nochnnel(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = []
        componentgroup = {"mycp": True}

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.mycps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.mydss)])

        se["AutomaticDataSources"] = json.dumps(poolchannels)
        se["AutomaticComponentGroup"] = json.dumps(componentgroup)
        res = se.updateAutomaticComponents(channelerrors)

        self.myAssertDict(json.loads(res), {"mycp": True})
        self.assertEqual(channelerrors, [])

        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ["AvailableComponents", "AvailableDataSources",
             "AvailableComponents", "Components"])
        self.assertEqual(json.loads(self._cf.dp.GetCommandVariable("VARS")),
                         [None, None, None, ['mycp']])
#        print self._cf.dp.availableComponents()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_wds(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = []
        componentgroup = {"smycp": True}

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.smycps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.smydss)])

        se["AutomaticDataSources"] = json.dumps(poolchannels)
        se["AutomaticComponentGroup"] = json.dumps(componentgroup)
        res = se.updateAutomaticComponents(channelerrors)

        self.myAssertDict(json.loads(res), {"smycp": True})
        self.assertEqual(channelerrors, [])

        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ["AvailableComponents", "AvailableDataSources",
             "AvailableComponents",
             "Components", "DataSources",  "DataSources", "DataSources",
             "DataSources"])

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_wds2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = []
        componentgroup = {"smycp": False, "smycp2": False, "smycp3": False}

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(self.smycps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(self.smydss)])

        se["AutomaticDataSources"] = json.dumps(poolchannels)
        se["AutomaticComponentGroup"] = json.dumps(componentgroup)
        res = se.updateAutomaticComponents(channelerrors)

        self.myAssertDict(json.loads(res), {
                "smycp": True, "smycp2": True, "smycp3": True})
        self.assertEqual(channelerrors, [])

        print self._cf.dp.GetCommandVariable("COMMANDS")
        self.assertEqual(
            json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
            ["AvailableComponents", "AvailableDataSources",
             "AvailableComponents",
             "Components", "DataSources",  "DataSources",  "DataSources",
             "DataSources",
             "Components", "DataSources",  "DataSources", "DataSources",
             "DataSources",
             "Components", "DataSources",  "DataSources", "DataSources",
             "DataSources"])
        res = json.loads(self._cf.dp.GetCommandVariable("VARS"))

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []
            poolchannels = []
            componentgroup = {"smycp": False, "smycp2": False, "smycp3": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True})
            self.assertEqual(len(channelerrors), 0)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            self.assertEqual(
                json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
                             [
                    "AvailableComponents", "AvailableDataSources",
                    "AvailableComponents",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources"])
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_dvnorunning(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.add()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []
            poolchannels = []
            componentgroup = {"smycp": False, "smycp2": False, "smycp3": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": False, "s2mycp2": False, "s2mycp3": False})
            self.assertEqual(len(channelerrors), 3)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            self.assertEqual(
                json.loads(self._cf.dp.GetCommandVariable("COMMANDS")),
                             [
                    "AvailableComponents", "AvailableDataSources",
                    "AvailableComponents",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources",
                    "Components", "DataSources", "DataSources", "DataSources",
                    "DataSources"])
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.delete()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_dvnodef(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        msp = MacroServerPools(1)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        channelerrors = []
        poolchannels = []
        componentgroup = {"smycp": False, "smycp2": False, "smycp3": False,
                          "s2mycp": False, "s2mycp2": False, "s2mycp3": False}

        cps = dict(self.smycps)
        cps.update(self.smycps2)
        dss = dict(self.smydss)
        dss.update(self.smydss2)

        self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
        self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

        se["AutomaticDataSources"] = json.dumps(poolchannels)
        se["AutomaticComponentGroup"] = json.dumps(componentgroup)
        res = se.updateAutomaticComponents(channelerrors)

        self.myAssertDict(json.loads(res), {
                "smycp": True, "smycp2": True, "smycp3": True,
                "s2mycp": False, "s2mycp2": False, "s2mycp3": False})
        self.assertEqual(len(channelerrors), 3)

        self.assertEqual(json.loads(
                self._cf.dp.GetCommandVariable("COMMANDS")),
                         [
                "AvailableComponents", "AvailableDataSources",
                "AvailableComponents",
                "Components", "DataSources", "DataSources", "DataSources",
                "DataSources",
                "Components", "DataSources", "DataSources", "DataSources",
                "DataSources",
                "Components", "DataSources", "DataSources", "DataSources",
                "DataSources",
                "Components", "DataSources", "DataSources", "DataSources",
                "DataSources",
                "Components", "DataSources", "DataSources", "DataSources",
                "DataSources",
                "Components", "DataSources", "DataSources", "DataSources",
                "DataSources"])
        res = json.loads(self._cf.dp.GetCommandVariable("VARS"))

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_nods(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []
            poolchannels = []
            componentgroup = {"smycp": False, "smycp2": False, "smycp3": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
#            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True})
            self.assertEqual(len(channelerrors), 0)

            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_nodspool(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short"]
            componentgroup = {"smycp": False, "smycp2": False, "smycp3": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
#            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": False, "s2mycp2": False, "s2mycp3": True})
            self.assertEqual(len(channelerrors), 2)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangods(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []

            poolchannels = ["scalar2_long", "spectrum2_short"]
            componentgroup = {"smycp": False, "smycp2": False,
                              "smycp3": False, "smycpnt1": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": True})
            self.assertEqual(len(channelerrors), 0)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodsnopool(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short", "client_long"]
            componentgroup = {"smycp": False, "smycp2": False,
                              "smycp3": False, "smycpnt1": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": False})
            self.assertEqual(len(channelerrors), 1)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodsnopool2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")
        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short", "client_long"]
            componentgroup = {"smycp": False, "smycp2": False,
                              "smycp3": False, "smycpnt1": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            print "POOLS", pools

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": False})
            self.assertEqual(len(channelerrors), 1)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangods2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_long", "full_name":"ttestp09/testts/t1r228/Value"},
            {"name":"client_short",
             "full_name":"ttestp09/testts/t1r228/Value"},
            ]

        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            channelerrors = []
            poolchannels = []
            componentgroup = {"smycp": False, "smycp2": False,
                              "smycp3": False, "smycpnt1": False,
                              "s2mycp": False, "s2mycp2": False,
                              "s2mycp3": False}

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])

            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            pools[0].AcqChannelList = [json.dumps(a) for a in arr]
            print "POOLS", pools

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": True})
            self.assertEqual(len(channelerrors), 0)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodspool_error(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_long", "full_name":"ttestp09/testts/t1r228/Value"},
            {"name":"client_short",
             "full_name":"ttestp09/testts/t1r228/Value"},
            ]

        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short", "client_long",
                            "client_short"]
            componentgroup = {
                "smycp": False, "smycp2": False, "smycp3": False,
                "smycpnt1": False,
                "s2mycp": False, "s2mycp2": False, "s2mycp3": False
                }

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])
    #        print "MDSS", self._cf.dp.availableDataSources()
    #        print "XDSS", self._cf.dp.dataSources(["scalar_long"])
            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            pools[0].AcqChannelList = [json.dumps(a) for a in arr]
            print "POOLS", pools

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            print res
    #        print channelerrors

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": False})
            self.assertEqual(len(channelerrors), 1)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodspool(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_short", "full_name":"ttestp09/testts/t1r228"},
            ]

        try:
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            db = PyTango.Database()
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})
            channelerrors = []

            poolchannels = ["scalar2_long", "spectrum2_short",  "client_short"]
            componentgroup = {
                "smycp": False, "smycp2": False, "smycp3": False,
                "smycpnt1": False,
                "s2mycp": False, "s2mycp2": False, "s2mycp3": False
                }

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])
    #        print "MDSS", self._cf.dp.availableDataSources()
    #        print "XDSS", self._cf.dp.dataSources(["scalar_long"])
            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            pools[0].AcqChannelList = [json.dumps(a) for a in arr]
            print "POOLS", pools
            self._simps.dp.ChangeValueType("ScalarShort")
            self._simps.dp.Value = 43

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": False})
            self.assertEqual(len(channelerrors), 1)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

   ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodspool_alias(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_short", "full_name":"ttestp09/testts/t1r228"},
            ]

        try:
            db = PyTango.Database()
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            db.put_device_alias(arr[0]["full_name"], arr[0]["name"])
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})

            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short", "client_short"]
            componentgroup = {
                "smycp": False, "smycp2": False, "smycp3": False,
                "smycpnt1": False,
                "s2mycp": False, "s2mycp2": False, "s2mycp3": False
                }

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])
            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            pools[0].AcqChannelList = [json.dumps(a) for a in arr]
            print "POOLS", pools
            self._simps.dp.ChangeValueType("ScalarShort")
            self._simps.dp.Value = 43

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": True})
            self.assertEqual(len(channelerrors), 0)

            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            db.delete_device_alias(arr[0]["name"])
            simps2.tearDown()

   ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodspool_alias_value(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_short", "full_name":"ttestp09/testts/t1r228"},
            ]

        try:
            db = PyTango.Database()
            simps2.setUp()
            msp = MacroServerPools(10)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            db.put_device_alias(arr[0]["full_name"], arr[0]["name"])
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})

            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short", "client_short"]
            componentgroup = {
                "smycp": False, "smycp2": False, "smycp3": False,
                "smycpnt1": False,
                "s2mycp": False, "s2mycp2": False, "s2mycp3": False
                }

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])
            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            pools[0].AcqChannelList = [json.dumps(a) for a in arr]
            print "POOLS", pools

            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": True, "s2mycp2": True, "s2mycp3": True,
                    "smycpnt1": True})
            self.assertEqual(len(channelerrors), 0)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            db.delete_device_alias(arr[0]["name"])
            simps2.tearDown()

  ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_notangodspool_alias_novalue(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_short", "full_name":"ttestp09/testts/t1r228"},
            ]

        try:
            db = PyTango.Database()
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]
            db.put_device_alias(arr[0]["full_name"], arr[0]["name"])
            db.put_device_property(self._ms.ms.keys()[0],
                                   {'PoolNames': self._pool.dp.name()})

            channelerrors = []
            poolchannels = ["scalar2_long", "spectrum2_short", "client2_short"]
            componentgroup = {
                "smycp": False, "smycp2": False, "smycp3": False,
                "s2mycpnt1": False,
#                "s2mycp": False, "s2mycp2": False, "s2mycp3": False
                }

            cps = dict(self.smycps)
            cps.update(self.smycps2)
            dss = dict(self.smydss)
            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])
            msp.updateMacroServer(self._ms.door.keys()[0])
            pools = msp.getPools(self._ms.door.keys()[0])
            pools[0].AcqChannelList = [json.dumps(a) for a in arr]
            print "POOLS", pools
            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycpnt1": False})
            self.assertEqual(len(channelerrors), 1)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            db.delete_device_alias(arr[0]["name"])
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_updateAutomaticComponents_2wds_nocomponents(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        simps2 = TestServerSetUp.TestServerSetUp(
            "ttestp09/testts/t2r228", "S2")

        arr = [
            {"name":"client_short", "full_name":"ttestp09/testts/t1r228"},
            ]

        try:
            db = PyTango.Database()
            simps2.setUp()
            msp = MacroServerPools(1)
            se = Selector(msp)
            se["ConfigDevice"] = val["ConfigDevice"]
            se["WriterDevice"] = val["WriterDevice"]

            channelerrors = []
            poolchannels = []
            componentgroup = {
                "smycp": False, "smycp2": False, "smycp3": False,
                "s2mycp": False, "s2mycp2": False, "s2mycp3": False}

            cps = dict(self.smycps)
#            cps.update(self.smycps2)
            dss = dict(self.smydss)
#            dss.update(self.smydss2)

            self._cf.dp.SetCommandVariable(["CPDICT", json.dumps(cps)])
            self._cf.dp.SetCommandVariable(["DSDICT", json.dumps(dss)])
    #        print "MDSS", self._cf.dp.availableDataSources()
    #        print "XDSS", self._cf.dp.dataSources(["scalar_long"])
            se["AutomaticDataSources"] = json.dumps(poolchannels)
            se["AutomaticComponentGroup"] = json.dumps(componentgroup)
            res = se.updateAutomaticComponents(channelerrors)

            self.myAssertDict(json.loads(res), {
                    "smycp": True, "smycp2": True, "smycp3": True,
                    "s2mycp": False, "s2mycp2": False, "s2mycp3": False})
            self.assertEqual(len(channelerrors), 3)

    #        print self._cf.dp.GetCommandVariable("COMMANDS")
            res = json.loads(self._cf.dp.GetCommandVariable("VARS"))
        finally:
            simps2.tearDown()

    ## constructor test
    # \brief It tests default settings
    def test_importEnv_noenv(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            pickle.dumps(
                {"new":{}
                 }
                )
            ]
        enms = [
            [],
            ["ScanID"],
            ["ScanDir", "ScanFile"],
            ]

        edats = [
            {},
            {},
            {}
            ]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        se.importEnv([], {})
        for i, dt in enumerate(edats):

            data = {}
            self._ms.dps[self._ms.ms.keys()[0]].Environment = (
                'pickle', envs[0])
            se.importEnv(enms[i], data)
#            print "data",data
            self.myAssertDict(data, dt)

    ## constructor test
    # \brief It tests default settings
    def test_importEnv(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}
        envs = [
            pickle.dumps(
                {"new":{"ScanDir":"/tmp"}
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp"}
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp", "ScanFile":["file.nxs"]}
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":["file.nxs"],
                        "NeXusConfigServer":"ptr/ert/ert",
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":["file.nxs", "file2.nxs"],
                        "NeXusConfiguration":{"ConfigServer":"ptr/ert/ert2"},
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":"file.nxs",
                        "NeXusConfigServer":"ptr/ert/ert",
                        "NeXusConfiguration":{"ConfigServer":"ptr/ert/ert2"},
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":["file.nxs"],
                        "NeXusConfigServer":u'ptr/ert/ert',
                        "NeXusBool": True,
                        "NeXusInt":234,
                        "NeXusFloat":123.123,
                        "NeXusSomething":("dgfg",),
                        "NeXusDict":{"dgfg":123, "sdf":"345"},
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":["file.nxs"],
                        "NeXusConfiguration":{"ConfigServer":u'ptr/ert/ert',
                        "Bool": True,
                        "Int":234,
                        "Float":123.123,
                        "Something":("dgfg",),
                        "Dict":{"dgfg":123, "sdf":"345"}}
                        }
                 }
                ),
            ]
        enms = [
            ["ScanID"],
            ["ScanDir"],
            ["ScanDir", "ScanFile", "ConfigServer"],
            ["ScanDir", "ScanFile", "ConfigServer"],
            ["ScanDir", "ScanFile", "ConfigServer"],
            ["ScanDir", "ScanFile", "ConfigServer"],
            ["ScanDir", "ScanFile", "ConfigServer", "Bool", "Int", "Float",
             "Something", "Dict"],
            ["ScanDir", "ScanFile", "ConfigServer", "Bool", "Int", "Float",
             "Something", "Dict"],
            ]

        edats = [
            {},
            {"ScanDir":"/tmp"},
            {"ScanDir":"/tmp", "ScanFile":json.dumps(["file.nxs"])},
            {"ScanDir":"/tmp",
             "ScanFile":json.dumps(["file.nxs"]),
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp",
             "ScanFile":json.dumps(["file.nxs", "file2.nxs"]),
             "ConfigServer":"ptr/ert/ert2"},
            {"ScanDir":"/tmp", "ScanFile":"file.nxs",
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp", "ScanFile":json.dumps(["file.nxs"]),
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.123,
             "Something":json.dumps(["dgfg"]),
             "Dict":json.dumps({"dgfg":123, "sdf":"345"}),
             },
            {"ScanDir":"/tmp", "ScanFile":json.dumps(["file.nxs"]),
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.123,
             "Something":json.dumps(["dgfg"]),
             "Dict":json.dumps({"dgfg":123, "sdf":"345"}),
             },
            ]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        se.importEnv([], {})
        for i, dt in enumerate(edats):
#            print "I = ",i
            data = {}
            self._ms.dps[self._ms.ms.keys()[0]].Environment = (
                'pickle', envs[i])
            se.importEnv(enms[i], data)
            self.myAssertDict(data, dt)

    ## constructor test
    # \brief It tests default settings
    def test_exportEnv(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)

        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            {"new":{'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'NeXusConfiguration': {},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp/'}
             },
            {"new":{
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'NeXusConfiguration': {},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp'}
             },
            {"new":{
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'NeXusConfiguration': {},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanDir":"/tmp",
                    "ScanFile":["file.nxs"]
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'NeXusConfiguration': {"ConfigServer":"ptr/ert/ert"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'NeXusConfiguration': {"ConfigServer":"ptr/ert/ert2"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs", "file2.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'NeXusConfiguration': {"ConfigServer":"ptr/ert/ert"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":"file.nxs",
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "NeXusConfiguration":{
                        "ConfigServer":'ptr/ert/ert',
                        "Bool": True,
                        "Int":234,
                        "Float":123.123,
                        "Something":["dgfg"],
                        "Dict":{"dgfg":123, "sdf":"345"}},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "NeXusConfiguration":{
                        "ConfigServer":'ptr/ert/ert',
                        "Bool": True,
                        "Int":234,
                        "Float":123.124,
                        "Something":["dgfg"],
                        "Dict":{"dgfg":123, "sdf":"345"}},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "NeXusConfiguration":{
                        "ConfigServer":'ptr/ert/ert',
                        "Bool": True,
                        "Int":234,
                        "Float":123.124,
                        "Something":["dgfg"],
                        "Dict":{"dgfg":123, "sdf":"345"},
                        "CConfigServer":'ptr/ert/ert',
                        "CBool": True,
                        "CInt":234,
                        "CFloat":123.124,
                        "CSomething":["dgfg"],
                        "CDict":{"dgfg":123, "sdf":"345"}
                        },
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "NeXusConfiguration":{
                        "ConfigServer":'ptr/ert/ert',
                        "Bool": True,
                        "Int":234,
                        "Float":123.124,
                        "Something":["dgfg"],
                        "Dict":{"dgfg":123, "sdf":"345"},
                        "CConfigServer":'ptr/ert/ert',
                        "CBool": True,
                        "CInt":234,
                        "CFloat":123.124,
                        "CSomething":json.dumps(["dgfg"]),
                        "CDict":json.dumps({"dgfg":123, "sdf":"345"})
                        },
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
           ]

        edats = [
            {},
            {"ScanDir":"/tmp"},
            {"ScanDir":"/tmp", "ScanFile":json.dumps(["file.nxs"])},
            {"ScanDir":"/tmp", "ScanFile":json.dumps(["file.nxs"]),
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp",
             "ScanFile":json.dumps(["file.nxs", "file2.nxs"]),
             "ConfigServer":"ptr/ert/ert2"},
            {"ScanDir":"/tmp", "ScanFile":"file.nxs",
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp", "ScanFile":json.dumps(["file.nxs"]),
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.123,
             "Something":json.dumps(["dgfg"]),
             "Dict":json.dumps({"dgfg":123, "sdf":"345"}),
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            ]

        cmds = [None, None, {}, None, None, None, None, None,
                {"CConfigServer":'ptr/ert/ert',
                 "CBool": True,
                 "CInt":234,
                 "CFloat":123.124,
                 "CSomething":["dgfg"],
                 "CDict":{"dgfg":123, "sdf":"345"}},
                 {"CConfigServer":'ptr/ert/ert',
                  "CBool": True,
                  "CInt":234,
                  "CFloat":123.124,
                  "CSomething":json.dumps(["dgfg"]),
                  "CDict":json.dumps({"dgfg":123, "sdf":"345"})},
                ]
        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        se.exportEnv({})
        se.exportEnv({}, {})
        for i, dt in enumerate(edats):
            se.exportEnv(dt, cmds[i])
#            print "I = ",i
            data = {}
            env = pickle.loads(
                self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
#            print "env", env
#            print "ei", envs[i]
            self.myAssertDict(envs[i], env)

    ## constructor test
    # \brief It tests default settings
    def test_fetchEnvData(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            pickle.dumps(
                {"new":{"ScanDir":"/tmp"}
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp", "ScanID": 11}
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp", "ScanFile":["file.nxs"]}
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",  "ScanID": 13,
                        "ScanFile":["file.nxs"],
                        "NeXusConfigServer":"ptr/ert/ert",
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":["file.nxs", "file2.nxs"],
                        "NeXusSelectorDevice": "p09/nxsrecselector/1",
                        "NeXusConfiguration":{"ConfigServer":"ptr/ert/ert2"},
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",  "ScanID": 15,
                        "ScanFile":"file.nxs",
                        "NeXusSelectorDevice": "p09/nxsrecselector/1",
                        "NeXusConfigServer":"ptr/ert/ert",
                        "NeXusConfiguration":{"ConfigServer":"ptr/ert/ert2"},
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",
                        "ScanFile":["file.nxs"],
                        "NeXusConfigServer":u'ptr/ert/ert',
                        "NeXusBool": True,
                        "NeXusInt":234,
                        "NeXusSelectorDevice": "p09/nxsrecselector/1",
                        "NeXusFloat":123.123,
                        "NeXusSomething":("dgfg",),
                        "NeXusDict":{"dgfg":123, "sdf":"345"},
                        }
                 }
                ),
            pickle.dumps(
                {"new":{"ScanDir":"/tmp",  "ScanID": 17,
                        "ScanFile":["file.nxs"],
                        "NeXusSelectorDevice": "p09/nxsrecselector/1",
                        "NeXusConfiguration":{"ConfigServer":u'ptr/ert/ert',
                        "Bool": True,
                        "Int":234,
                        "Float":123.123,
                        "Something":("dgfg",),
                        "Dict":{"dgfg":123, "sdf":"345"}}
                        }
                 }
                ),
            ]

        edats = [
            {"ScanDir":"/tmp"},
            {"ScanDir":"/tmp", "ScanID": 11},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"]},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"], "ScanID": 13},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs", "file2.nxs"],
             "NeXusSelectorDevice": "p09/nxsrecselector/1"},
            {"ScanDir":"/tmp", "ScanFile":"file.nxs", "ScanID": 15,
             "NeXusSelectorDevice": "p09/nxsrecselector/1"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "NeXusSelectorDevice": "p09/nxsrecselector/1"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"], "ScanID": 17,
             "NeXusSelectorDevice": "p09/nxsrecselector/1"},
            ]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        data = {"ScanID": 192,
                "NeXusSelectorDevice": "p09/nxsrecselector/1",
                "ScanFile": ["sar4r.nxs"], "ScanDir": "/tmp/"}
        res = se.fetchEnvData()
        self.myAssertDict(json.loads(res), data)
        for i, dt in enumerate(edats):
#            print "I = ",i
            data = {}
            self._ms.dps[self._ms.ms.keys()[0]].Environment = (
                'pickle', envs[i])
            dt = se.fetchEnvData()
#            print edats[i]
#            print "data",dt
            self.myAssertDict(edats[i], json.loads(dt))

    ## constructor test
    # \brief It tests default settings
    def test_storeEnvData(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            {"new":{'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp/'}
             },
            {"new":{
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp'}
             },
            {"new":{
                    'ScanID': 11,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanDir":"/tmp",
                    "ScanFile":["file.nxs"]
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 11,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 13,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert2",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs", "file2.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 13,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":"file.nxs",
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 15,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.123,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 15,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 17,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 17,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
           ]

        edats = [
            {},
            {"ScanDir":"/tmp"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"], "ScanID":11},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs", "file2.nxs"],
             "ConfigServer":"ptr/ert/ert2", "ScanID":13},
            {"ScanDir":"/tmp", "ScanFile":"file.nxs",
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert", "ScanID":15,
             "Bool": True, "Int":234, "Float":123.123, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert", "ScanID":17,
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            ]

        sids = [192, 192, 11, 11, 13, 13, 15, 15, 17, 17]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        se.storeEnvData("{}")
        for i, dt in enumerate(edats):
            sid = se.storeEnvData(json.dumps(dt))
            print "I = ", i, sid
            self.assertEqual(sid, sids[i])
            data = {}
            env = pickle.loads(
                self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
#            print "env", env
#            print "ei", envs[i]
            self.myAssertDict(envs[i], env)

    ## constructor test
    # \brief It tests default settings
    def test_setScanEnv_scanid(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            pickle.dumps(
                {"new":{}
                     }
                ),
            pickle.dumps(
                {"new":{"ScanID":12}
                     }
                )
            ]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]

        self.assertEqual(se.storeEnvData("{}"), 192)
        self._ms.dps[self._ms.ms.keys()[0]].Environment = ('pickle', envs[0])
        self.assertEqual(se.storeEnvData("{}"), -1)
        self._ms.dps[self._ms.ms.keys()[0]].Environment = ('pickle', envs[1])
        self.assertEqual(se.storeEnvData("{}"), 12)

    ## constructor test
    # \brief It tests default settings
    def test_setScanEnv2(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            {"new":{'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp/'}
             },
            {"new":{
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp'}
             },
            {"new":{
                    'ScanID': 11,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanDir":"/tmp",
                    "ScanFile":["file.nxs"]
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 11,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 13,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert2",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs", "file2.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 13,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":"file.nxs",
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 15,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.123,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 15,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 17,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 17,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int":234,
                    "Float":123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg": 123, "sdf": "345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
           ]

        edats = [
            {},
            {"ScanDir":"/tmp"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"], "ScanID":11},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs", "file2.nxs"],
             "ConfigServer":"ptr/ert/ert2", "ScanID":13},
            {"ScanDir":"/tmp", "ScanFile":"file.nxs",
             "ConfigServer":"ptr/ert/ert"},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert", "ScanID":15,
             "Bool": True, "Int":234, "Float":123.123, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert", "ScanID":17,
             "Bool": True, "Int":234, "Float":123.124, "Something":["dgfg"],
             "Dict": {"dgfg":123, "sdf":"345"},
             },
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert",
             "Bool": True, "Int": 234, "Float": 123.124, "Something":["dgfg"],
             "Dict":{"dgfg": 123, "sdf": "345"},
             },
            ]

        sids = [192, 192, 11, 11, 13, 13, 15, 15, 17, 17]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        se.storeEnvData("{}")
        for i, dt in enumerate(edats):
            sid = se.storeEnvData(json.dumps(dt))
            print "I = ", i, sid
            self.assertEqual(sid, sids[i])
            data = {}
            env = pickle.loads(
                self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
#            print "env", env
#            print "ei", envs[i]
            self.myAssertDict(envs[i], env)

    ## constructor test
    # \brief It tests default settings
    def test_setScanEnv_dtlist(self):
        fun = sys._getframe().f_code.co_name
        print "Run: %s.%s() " % (self.__class__.__name__, fun)
        val = {"ConfigDevice": self._cf.dp.name(),
               "WriterDevice": self._wr.dp.name(),
               "Door": 'doortestp09/testts/t1r228',
               "MntGrp": 'nxsmntgrp'}

        envs = [
            {"new":{'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp/'}
             },
            {"new":{
                    'ScanID': 192,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ScanFile': [u'sar4r.nxs'],
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    'ScanDir': '/tmp'}
             },
            {"new":{
                    'ScanID': "11",
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanDir":"/tmp",
                    "ScanFile":"file.nxs"
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': "11",
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":"file.nxs",
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': '13',
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert2",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":"file.nxs",
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 13,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":"ptr/ert/ert",
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":"file.nxs",
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 15,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int": 234,
                    "Float": 123.123,
                    "Something": ["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
            {"new":{"ScanDir":"/tmp",
                    'ScanID': 15,
                    'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                    "ConfigServer":'ptr/ert/ert',
                    "Bool": True,
                    "Int": 234,
                    "Float": 123.124,
                    "Something":["dgfg"],
                    "Dict":{"dgfg":123, "sdf":"345"},
                    'ActiveMntGrp': 'nxsmntgrp',
                    '_ViewOptions': {'ShowDial': True},
                    'DataCompressionRank': 0,
                    "ScanFile":["file.nxs"],
                    }
             },
           ]

        edats = [
            "",
            "ScanDir /tmp",
            "ScanDir:/tmp, ScanFile:file.nxs, ScanID:11",
            "ScanDir /tmp, ScanFile:file.nxs,ConfigServer ptr/ert/ert",
            "ScanDir:/tmp, ScanFile:file.nxs  ConfigServer:ptr/ert/ert2, "
            "ScanID:13",
            {"ScanDir":"/tmp", "ScanFile":"file.nxs",
             "ConfigServer":"ptr/ert/ert", "ScanID":13},
            {"ScanDir":"/tmp", "ScanFile":["file.nxs"],
             "ConfigServer":"ptr/ert/ert", "ScanID":15,
             "Bool": True, "Int":234, "Float":123.123, "Something":["dgfg"],
             "Dict":{"dgfg":123, "sdf":"345"},
             },
            ]

        sids = [192, 192, 11, 11, 13, 13, 15, 15, 17, 17]

        msp = MacroServerPools(10)
        se = Selector(msp)
        se["ConfigDevice"] = val["ConfigDevice"]
        se["WriterDevice"] = val["WriterDevice"]
        se.storeEnvData("{}")

        msp.setScanEnv(self._ms.door.keys()[0], "{}")
        for i, dt in enumerate(edats):
            env = pickle.loads(
                self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
            print "env0", env
            sid = se.storeEnvData(
                dt if not isinstance(dt, dict) else json.dumps(dt))
            print "I = ", i, sid
            self.assertEqual(sid, sids[i])
            data = {}
            env = pickle.loads(
                self._ms.dps[self._ms.ms.keys()[0]].Environment[1])
            print "env", env
            print "ei", envs[i]
            self.myAssertDict(envs[i], env)


if __name__ == '__main__':
    unittest.main()