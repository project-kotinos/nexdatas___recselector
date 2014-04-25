#!/usr/bin/env python
#   This file is part of nexdatas - Tango Server for NeXus data writer
#
#    Copyright (C) 2014 DESY, Jan Kotanski <jkotan@mail.desy.de>
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
## \file setup.py
# nxswriter installer 

""" setup.py for Nexus Recorder Selector Server """


import os
from distutils.core import setup

## package name
NDTS = "nxsrecconfig"
## nxswriter imported package
INDTS = __import__(NDTS)


#__requires__ = 'nextdata ==%s' % INDTS.__version__

## reading a file
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

## required files
required = [
    'numpy (>=1.5.0)',
    'PyTango (>=7.2.2)'
    ]

## metadata for distutils
SETUPDATA = dict(
    name = "nexdatas",
    version = INDTS.__version__,
    author = "Jan Kotanski",
    author_email = "jankotan@gmail.com",
    description = ("Selector Server for NeXus Sardana recorder"),
    license = "GNU GENERAL PUBLIC LICENSE v3",
    keywords = "sardana writer configuration settings Tango server nexus data",
    url = "www.desy.de",
    packages=[NDTS],
    requires=required,
    scripts = ['NXSRecSelector.py', 'NXSRecSelector'],
    long_description= read('README')
)


        

## the main function
def main():
    setup(**SETUPDATA)
        

if __name__ == '__main__':
    main()
