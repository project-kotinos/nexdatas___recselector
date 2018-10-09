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
# \package test nexdatas
# \file ServerSetUp.py
# class with server settings
#
import os
import sys
import subprocess

import PyTango
import time
import TestWriter


# test fixture
class TestWriterSetUp(object):

    # constructor
    # \brief defines server parameters

    def __init__(self, device="writertestp09/testts/t1r228",
                 instance="WRITERTESTS1"):
        # information about tango writer
        self.new_device_info_writer = PyTango.DbDevInfo()
        # information about tango writer class
        self.new_device_info_writer._class = "NXSDataWriter"
        # information about tango writer server
        self.new_device_info_writer.server = "NXSDataWriter/%s" % instance
        # information about tango writer name
        self.new_device_info_writer.name = device

        # server instance
        self.instance = instance
        self._psub = None
        # device proxy
        self.dp = None
        # device properties

    # test starter
    # \brief Common set up of Tango Server
    def setUp(self):
        print("\nsetting up...")
        self.add()
        self.start()

    def add(self):
        db = PyTango.Database()
        db.add_device(self.new_device_info_writer)
        db.add_server(self.new_device_info_writer.server,
                      self.new_device_info_writer)

    # starts server
    def start(self):
        path = os.path.dirname(TestWriter.__file__)
        if not path:
            path = '.'

        self._psub = subprocess.call(
            "cd %s;  python ./TestWriter.py %s &" % (path, self.instance),
            stdout=None,
            stderr=None, shell=True)
        sys.stdout.write("waiting for simple server")

        found = False
        cnt = 0
        while not found and cnt < 1000:
            try:
                sys.stdout.write(".")
                self.dp = PyTango.DeviceProxy(self.new_device_info_writer.name)
                time.sleep(0.01)
                if self.dp.state() == PyTango.DevState.ON:
                    found = True
            except:
                found = False
            cnt += 1
        print("")

    # test closer
    # \brief Common tear down of Tango Server
    def tearDown(self):
        print("tearing down ...")
        self.delete()
        self.stop()

    def delete(self):
        db = PyTango.Database()
        db.delete_server(self.new_device_info_writer.server)

    # stops server
    def stop(self):
        pipe = subprocess.Popen(
            "ps -ef | grep 'TestWriter.py %s'" % self.instance,
            stdout=subprocess.PIPE, shell=True).stdout

        res = pipe.read().split("\n")
        for r in res:
            sr = r.split()
            if len(sr) > 2:
                subprocess.call(
                    "kill -9 %s" % sr[1], stderr=subprocess.PIPE, shell=True)


if __name__ == "__main__":
    simps = TestWriterSetUp()
    simps.setUp()
    print(simps.dp.status())
    simps.tearDown()
