#!/usr/bin/env python
#   This file is part of nxsrecconfig - NeXus Sardana Recorder Settings
#
#    Copyright (C) 2014-2015 DESY, Jan Kotanski <jkotan@mail.desy.de>
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
## \file Profile.py
# tango utilities

"""  Profile """

import json

from .Utils import TangoUtils, PoolUtils, MSUtils, Utils
from .Describer import Describer

try:
    from nxstools.nxsxml import (XMLFile, NDSource)
    ## flag for nxstools installed
    NXSTOOLS = True
except ImportError:
    NXSTOOLS = False

DEFAULT_RECORD_KEYS = ['serialno', 'end_time', 'start_time',
                       'point_nb', 'timestamps', 'scan_title']


## Profile class
class Profile(object):
    """  MntGrp Tools """

    ## constructor
    # \param selector selector object
    def __init__(self, selector):
        ## configuration selector
        self.__selector = selector
        ## default mntgrp
        self.__defaultmntgrp = 'nxsmntgrp'

        ## macro server name
        self.__macroServerName = None
        ## configuration server proxy
        self.__configServer = None
        ## pool server proxies
        self.__pools = None

        ## default automaticComponents
        self.defaultAutomaticComponents = []
        ## error descriptions
        self.descErrors = []

    def __updateMacroServer(self):
        self.__macroServerName = self.__selector.getMacroServer()

    def __updateConfigServer(self):
        self.__configServer = self.__selector.setConfigInstance()

    def __updatePools(self):
        self.__pools = self.__selector.getPools()

    ## available mntgrps
    # \returns list of available measurement groups
    def availableMntGrps(self):
        self.__updateMacroServer()
        self.__updatePools()
        mntgrps = None
        pool = None
        self.__updatePools()
        fpool = None
        for pool in self.__pools:
            if not fpool:
                fpool = pool
                break
        if fpool:
            mntgrps = PoolUtils.getMntGrps([fpool])
        mntgrps = mntgrps if mntgrps else []
        amntgrp = MSUtils.getEnv('ActiveMntGrp', self.__macroServerName)

        try:
            if mntgrps:
                ind = mntgrps.index(amntgrp)
                mntgrps[0], mntgrps[ind] = mntgrps[ind], mntgrps[0]
        except ValueError:
            pass
        return mntgrps

    ## provides configuration of mntgrp
     # \returns string with mntgrp configuration
    def mntGrpConfiguration(self):
        self.__updatePools()
        self.__updateMacroServer()
        if not self.__selector["MntGrp"]:
            self.switch(toActive=False)
        mntGrpName = self.__selector["MntGrp"]
        fullname = str(PoolUtils.getMntGrpName(self.__pools, mntGrpName))
        dpmg = TangoUtils.openProxy(fullname) if fullname else None
        if not dpmg:
            return "{}"
        return str(dpmg.Configuration)

    ## check if active measurement group was changed
    # \param components  component list
    # \param datasources datasource list
    # \param disabledatasources disable datasource list
    # \returns True if it is different to the current setting
    def isMntGrpChanged(self, components, datasources, disabledatasources):
        mgconf = json.loads(self.mntGrpConfiguration())
        self.__updateConfigServer()
        llconf, _ = self.__createMntGrpConf(
            components, datasources, disabledatasources)
        self.store()
        lsconf = json.loads(llconf)
        return not Utils.compareDict(mgconf, lsconf)

    ## import setting from active measurement
    def importMntGrp(self):
        self.__updateMacroServer()
        self.__updateConfigServer()
        jconf = self.mntGrpConfiguration()
        if self.__setFromMntGrpConf(jconf):
            self.store()

    ## set active measurement group from components
    # \param components  component list
    # \param datasources datasource list
    # \param disabledatasources disable datasource list
    # \returns string with mntgrp configuration
    def update(self, components, datasources, disabledatasources):
        self.__updateConfigServer()
        conf, mntgrp = self.__createMntGrpConf(
            components, datasources, disabledatasources)
        self.store()
        dpmg = TangoUtils.openProxy(mntgrp)
        dpmg.Configuration = conf
        return str(dpmg.Configuration)

    ## switch to active measurement
    def switch(self, toActive=True):
        if not self.__selector["MntGrp"] or toActive:
            ms = self.__selector.getMacroServer()
            amntgrp = MSUtils.getEnv('ActiveMntGrp', ms)
            if not toActive or amntgrp:
                self.__selector["MntGrp"] = amntgrp
        self.fetch()
        jconf = self.mntGrpConfiguration()
        self.__updateConfigServer()
        if self.__setFromMntGrpConf(jconf):
            self.store()

    ## saves configuration
    def store(self):
        inst = self.__selector.setConfigInstance()
        conf = str(json.dumps(self.__selector.get()))
        inst.selection = conf
        inst.storeSelection(self.__selector["MntGrp"])

    ## fetch configuration
    def fetch(self):
        inst = self.__selector.setConfigInstance()
        avsl = inst.availableSelections()
        confs = None
        if self.__selector["MntGrp"] in avsl:
            confs = inst.selections([self.__selector["MntGrp"]])
        if confs:
            self.__selector.set(json.loads(str(confs[0])))
        else:
            avmg = self.availableMntGrps()
            if self.__selector["MntGrp"] in avmg:
                self.__selector.deselect()
                self.importMntGrp()
                self.__selector.resetAutomaticComponents(
                    self.defaultAutomaticComponents)
                self.updateAutomaticComponents()

    ## deletes mntgrp
    # \param name mntgrp name
    def delete(self, name):
        self.__updatePools()
        fpool = None
        for pool in self.__pools:
            if not fpool:
                fpool = pool
                break
        if fpool:
            TangoUtils.command(
                fpool, "DeleteElement", str(name))
        inst = self.__selector.setConfigInstance()
        inst.deleteSelection(name)

    ## set active measurement group from components
    # \param components  component list
    # \param datasources datasource list
    # \param disabledatasources disable datasource list
    # \returns tuple of MntGrp configuration and MntGrp Device name
    def __createMntGrpConf(self, components, datasources, disabledatasources):
        self.__updatePools()
        self.__updateMacroServer()
        cnf = {}
        cnf['controllers'] = {}
        cnf['description'] = "Measurement Group"
        cnf['label'] = ""

        dontdisplay = set(json.loads(self.__selector["HiddenElements"]))

        ltimers = set()
        timer = self.__prepareTimers(cnf, ltimers)

        aliases = self.__fetchChannels(
            components, datasources, disabledatasources,
            dontdisplay, set(ltimers) | set([timer]))

        mfullname = self.__prepareMntGrp(cnf, timer)

        index = 0
        fullnames = PoolUtils.getFullDeviceNames(self.__pools, aliases)
        for al in aliases:
            index = self.__addDevice(
                al, dontdisplay, cnf,
                al if al in ltimers else timer, index, fullnames)
        conf = json.dumps(cnf)
        return conf, mfullname

    ## import setting from active measurement
    def __setFromMntGrpConf(self, jconf):
        self.__updatePools()
        conf = json.loads(jconf)
        otimers = None
        timers = {}

        dsg = json.loads(self.__selector["DataSourceGroup"])
        hel = json.loads(self.__selector["HiddenElements"])
        self.__clearChannels(dsg, hel)

        # fill in dsg, timers hel
        if "timer" in conf.keys() and "controllers" in conf.keys():
            tangods = self.__readChannels(conf, timers, dsg, hel)
            self.__readTangoChannels(conf, tangods, dsg, hel)
            otimers = self.__reorderTimers(conf, timers, dsg, hel)

        changed = False
        jdsg = json.dumps(dsg)
        if self.__selector["DataSourceGroup"] != jdsg:
            self.__selector["DataSourceGroup"] = jdsg
            changed = True

        jhel = json.dumps(hel)
        if self.__selector["HiddenElements"] != jhel:
            self.__selector["HiddenElements"] = jhel
            changed = True
        if otimers is not None:
            jtimers = json.dumps(otimers)
            if self.__selector["Timer"] != jtimers:
                self.__selector["Timer"] = jtimers
                changed = True
        return changed

    ## checks existing controllers of pools for
    #      AutomaticDataSources
    def updateAutomaticComponents(self):
        jacps = self.__selector.updateAutomaticComponents(self.descErrors)
        if self.__selector["AutomaticComponentGroup"] != jacps:
            self.__selector["AutomaticComponentGroup"] = jacps
            self.store()

    def __clearChannels(self, dsg, hel):
        channels = PoolUtils.getExperimentalChannels(self.__pools)
        for ch in channels:
            if ch in dsg.keys():
                dsg[ch] = False
            if ch in hel:
                hel.remove(ch)

    @classmethod
    def __readChannels(cls, conf, timers, dsg, hel):
        tangods = []
        timers[conf["timer"]] = ''
        for ctrl in conf["controllers"].values():
            if 'units' in ctrl.keys() and \
                    '0' in ctrl['units'].keys():
                if 'timer' in ctrl['units']['0'].keys():
                    timers[ctrl['units']['0']['timer']] = ''
                if 'channels' in ctrl['units']['0'].keys():
                    for ch in ctrl['units']['0']['channels'].values():
                        if '_controller_name' in ch.keys() and \
                                ch['_controller_name'] == '__tango__':
                            tangods.append(
                                [ch['name'], ch['label'], ch["source"]])
                        else:
                            dsg[ch['name']] = True
                            if not bool(ch['plot_type']):
                                hel.append(ch['name'])

        return tangods

    def __readTangoChannels(self, conf, tangods, dsg, hel):
        if tangods and NXSTOOLS:
            jds = self.__createDataSources(tangods, dsg)
            for ctrl in conf["controllers"].values():
                if 'units' in ctrl.keys() and \
                        '0' in ctrl['units'].keys():
                    if 'channels' in ctrl['units']['0'].keys():
                        for ch in ctrl['units']['0']['channels'].values():
                            if '_controller_name' in ch.keys() and \
                                    ch['_controller_name'] == '__tango__':
                                if ch["source"] in jds.keys():
                                    name = jds[ch["source"]]
                                    dsg[name] = True
                                    if not bool(ch['plot_type']):
                                        hel.append(ch['name'])

    def __reorderTimers(self, conf, timers, dsg, hel):
        dtimers = PoolUtils.getAliases(self.__pools, timers)
        otimers = list(dtimers.values())
        otimers.remove(dtimers[conf["timer"]])
        otimers.insert(0, dtimers[conf["timer"]])

        tms = json.loads(self.__selector["Timer"])
        tms.extend(otimers)

        hel2 = json.loads(self.__selector["HiddenElements"])
        for tm in tms:
            if tm in hel2:
                if tm in dsg.keys():
                    dsg[tm] = False
                if tm in hel:
                    hel.remove(tm)
        return otimers

    ## checks client records
    def __checkClientRecords(self, components, datasources):

        describer = Describer(self.__configServer, True)
        frecords = PoolUtils.getFullDeviceNames(self.__pools)
        dsres = describer.dataSources(
            set(datasources) - set(frecords.keys()), 'CLIENT')[0]
        records = [str(dsr.record) for dsr in dsres.values()]

        cpres = describer.components(components,
            '', 'CLIENT')
        for grp in cpres:
            for dss in grp.values():
                for dsrs in dss.values():
                    for dsr in dsrs:
                        records.append(str(dsr[2]))

        urecords = json.loads(self.__selector["DataRecord"]).keys()
        precords = frecords.values()
        missing = sorted(set(records)
                         - set(DEFAULT_RECORD_KEYS)
                         - set(urecords)
                         - set(precords))
        if missing:
            raise Exception(
                "User Data not defined %s" % str(missing))

    def __createMntGrpDevice(self, mntGrpName, timer):
        amntgrp = MSUtils.getEnv('ActiveMntGrp', self.__macroServerName)
        apool = None
        lpool = [None, 0]
        fpool = None
        for pool in self.__pools:
            if not fpool:
                fpool = pool
            mntgrps = PoolUtils.getMntGrps([pool])
            if amntgrp in mntgrps:
                apool = pool
            if lpool[1] < len(mntgrps):
                lpool = [pool, len(mntgrps)]

        if not apool:
            apool = lpool[0]
        lpool = None
        if not apool and fpool:
            apool = fpool
        fpool = None
        if not apool and len(self.__pools) > 0:
            apool = self.__pools[0]
        if apool:
            TangoUtils.command(apool, "CreateMeasurementGroup",
                          [mntGrpName, timer])
            mfullname = str(PoolUtils.getMntGrpName(self.__pools, mntGrpName))
        return mfullname

    ## prepares timers
    def __prepareTimers(self, cnf, ltimers):
        mtimers = json.loads(self.__selector["Timer"])
        timer = mtimers[0] if mtimers else ''
        if not timer:
            raise Exception(
                "Timer or Monitor not defined")
        fullname = PoolUtils.getFullDeviceNames(
            self.__pools, [timer])[timer]
        if not fullname:
            raise Exception(
                "Timer or Monitor cannot be found amount the servers")
        cnf['monitor'] = fullname
        cnf['timer'] = fullname
        if len(mtimers) > 1:
            ltimers.clear()
            ltimers.update(set(mtimers[1:]))
            if timer in ltimers:
                ltimers.remove(timer)
        return timer

    def __fetchChannels(self, components, datasources, disabledatasources,
                        dontdisplay, timers):
        aliases = []

        self.__checkClientRecords(components, datasources)
        if isinstance(datasources, list):
            aliases = list(datasources)
        pchannels = json.loads(self.__selector["OrderedChannels"])
        aliases.extend(
            list(set(pchannels) & set(disabledatasources)))

        describer = Describer(self.__configServer, True)
        res = describer.components(components, 'STEP', 'CLIENT')

        for grp in res:
            for cp, dss in grp.items():
                ndcp = cp in dontdisplay
                for ds in dss.keys():
                    aliases.append(str(ds))
                    if not ndcp and str(ds) in dontdisplay:
                        dontdisplay.remove(str(ds))

        self.__selector["HiddenElements"] = json.dumps(list(dontdisplay))
        aliases = list(set(aliases))

        for tm in timers:
            if tm not in aliases:
                aliases.append(tm)
                dontdisplay.add(tm)

        pchannels = [ch for ch in pchannels if ch in aliases]
        aliases = list(set(aliases) - set(pchannels))
        pchannels.extend(aliases)
        return pchannels

    ## sets mntgrp
    def __prepareMntGrp(self, cnf, timer):
        if not self.__selector["MntGrp"]:
            self.__selector["MntGrp"] = self.__defaultmntgrp
        mntGrpName = self.__selector["MntGrp"]
        mfullname = str(PoolUtils.getMntGrpName(self.__pools, mntGrpName))

        if not mfullname:
            mfullname = self.__createMntGrpDevice(mntGrpName, timer)

        MSUtils.setEnv('ActiveMntGrp', str(mntGrpName), self.__macroServerName)
        cnf['label'] = mntGrpName
        return mfullname

    @classmethod
    def __findSources(cls, tangods, extangods, exsource):
        for name, _, initsource in tangods:
            source = initsource if initsource[:8] != 'tango://' \
                else initsource[8:]
            msource = None
            spsource = source.split("/")
            if len(spsource) > 3 and ":" in spsource[0]:
                host, port = spsource[0].split(":")
                mhost = host.split(".")[0]
                msource = "/".join(spsource[1:])
                if mhost != host:
                    msource = "%s:%s/%s" % (mhost, port, msource)
                device = "/".join(spsource[1:-1])
                attribute = spsource[-1]
                exsource[source] = [host, port, device, attribute]
            extangods.append(
                [name, initsource, source, msource])

    @classmethod
    def __addKnownSources(cls, extangods, sds, existing=None):
        jds = {}
        found = set()
        if not existing:
            existing = []
        for ds in sds:
            js = json.loads(ds)
            if js["dsname"] in existing:
                for _, initsource, source, msource in extangods:
                    if source == js["record"]:
                        jds[initsource] = js["dsname"]
                        found.add(str(js["record"]))
                        break
                    elif msource == js["record"]:
                        jds[initsource] = js["dsname"]
                        found.add(str(js["record"]))
                        break
        for ds in sds:
            js = json.loads(ds)
            if js["dsname"] not in existing and \
                    js["record"] not in found:
                for _, initsource, source, msource in extangods:
                    if source == js["record"]:
                        jds[initsource] = js["dsname"]
                        found.add(str(js["dsname"]))
                        break
                    elif msource == js["record"]:
                        jds[initsource] = js["dsname"]
                        found.add(str(js["dsname"]))
                        break
        return jds

    @classmethod
    def __createXMLSource(cls, name, source, exsource):
        host, port, device, attribute = exsource[source]
        df = XMLFile("ds.xml")
        sr = NDSource(df)
        sr.initTango(
            name, device, "attribute", attribute, host, port,
            group='__CLIENT__')
        return df.prettyPrint()

    def __createUnknownSources(self, extangods, exsource, ads, jds):
        for name, initsource, source, _ in extangods:
            if initsource not in jds:
                jds[initsource] = None
                i = 0
                nname = name
                while nname in ads:
                    i += 1
                    nname = "%s_%s" % (name, i)
                name = nname
                if source in exsource:
                    xml = self.__createXMLSource(name, source, exsource)
                    self.__configServer.xmlstring = str(xml)
                    TangoUtils.command(self.__configServer, "storeDataSource",
                                  str(name))
                    jds[initsource] = name

    def __createDataSources(self, tangods, dsg):
        extangods = []
        exsource = {}

        ads = TangoUtils.command(self.__configServer, "availableDataSources")
        if not ads:
            ads = []
        describer = Describer(self.__configServer)
        sds = describer.dataSources(ads)
        self.__findSources(tangods, extangods, exsource)
        jds = self.__addKnownSources(extangods, sds, dsg.keys())
        self.__createUnknownSources(extangods, exsource, ads, jds)
        return jds

    ## adds device into configuration dictionary
    # \param cls class instance
    # \param device device alias
    # \param dontdisplay list of devices disable for display
    # \param cnf configuration dictionary
    # \param timer device timer
    # \param index device index
    # \param fullnames dictionary with full names
    # \returns next device index
    def __addDevice(self, device, dontdisplay, cnf,
                  timer, index, fullnames=None):
        if not fullnames:
            fullnames = PoolUtils.getFullDeviceNames(
                self.__pools, [device, timer])

        ctrls = PoolUtils.getDeviceControllers(self.__pools, [device])
        ctrl = ctrls[device] if ctrls and device in ctrls.keys() else ""
        timers = PoolUtils.getFullDeviceNames(self.__pools, [timer])
        fulltimer = fullnames[timer] \
            if timers and timer in fullnames.keys() else ""
        if ctrl:
            self.__addController(cnf, ctrl, fulltimer)
            fullname = fullnames[device] \
                if fullnames and device in fullnames.keys() else ""
            index = self.__addChannel(cnf, ctrl, device, fullname,
                                     dontdisplay, index)
        else:
            describer = Describer(self.__configServer)
            sds = describer.dataSources([device])
            if sds:
                js = json.loads(sds[0])
                if js["dstype"] == 'TANGO':
                    ctrl = "__tango__"
                    self.__addController(cnf, ctrl, fulltimer)
                    index = self.__addTangoChannel(
                        cnf, ctrl, device, str(js["record"]),
                        dontdisplay, index)

        return index

    ## adds controller into configuration dictionary
    @classmethod
    def __addController(cls, cnf, ctrl, fulltimer):
        if 'controllers' not in cnf.keys():
            cnf['controllers'] = {}
        if not ctrl in cnf['controllers'].keys():
            cnf['controllers'][ctrl] = {}
            cnf['controllers'][ctrl]['units'] = {}
            cnf['controllers'][ctrl]['units']['0'] = {}
            cnf['controllers'][ctrl]['units']['0'][
                u'channels'] = {}
            cnf['controllers'][ctrl]['units']['0']['id'] = 0
            cnf['controllers'][ctrl]['units']['0'][
                u'monitor'] = fulltimer
            cnf['controllers'][ctrl]['units']['0'][
                u'timer'] = fulltimer
            cnf['controllers'][ctrl]['units']['0'][
                u'trigger_type'] = 0

    ## adds channel into configuration dictionary
    @classmethod
    def __addChannel(cls, cnf, ctrl, device, fullname, dontdisplay, index):

        ctrlChannels = cnf['controllers'][ctrl]['units']['0'][
            u'channels']
        if not fullname in ctrlChannels.keys():
            source = PoolUtils.getSource(fullname)
            if not source:
                source = '%s/%s' % (fullname.encode(), 'Value')
            shp, dt, ut = TangoUtils.getShapeTypeUnit(source)
            dct = {}
            dct['_controller_name'] = unicode(ctrl)
            dct['_unit_id'] = u'0'
            dct['conditioning'] = u''
            dct['data_type'] = dt
            dct['data_units'] = ut
            dct['enabled'] = True
            dct['full_name'] = fullname
            dct['index'] = index
            index += 1
            dct['instrument'] = None
            dct['label'] = unicode(device)
            dct['name'] = unicode(device)
            dct['ndim'] = 0
            dct['nexus_path'] = u''
            dct['normalization'] = 0
            dct['output'] = True
            dct['shape'] = shp

            if device in dontdisplay:
                dct['plot_axes'] = []
                dct['plot_type'] = 0
            elif dct['shape'] and len(dct['shape']) == 1:
                dct['plot_axes'] = ['<idx>']
                dct['plot_type'] = 1
            elif dct['shape'] and len(dct['shape']) == 2:
                dct['plot_axes'] = ['<idx>', '<idx>']
                dct['plot_type'] = 2
            else:
                dct['plot_axes'] = ['<mov>']
                dct['plot_type'] = 1

            dct['source'] = source
            ctrlChannels[fullname] = dct

        return index

    ## adds  tango channel into configuration dictionary
    @classmethod
    def __addTangoChannel(cls, cnf, ctrl, device, record, dontdisplay, index):

        ctrlChannels = cnf['controllers'][ctrl]['units']['0'][
            u'channels']
        fullname = "tango://%s" % record
        srecord = record.split("/")
        if srecord and len(srecord) > 1 and ":" in srecord[0]:
            label = "/".join(srecord[1:])
        else:
            label = record
        if not fullname in ctrlChannels.keys():
            source = record
            shp, dt, ut = TangoUtils.getShapeTypeUnit(source)
            dct = {}
            dct['_controller_name'] = unicode(ctrl)
            dct['_unit_id'] = u'0'
            dct['conditioning'] = u''
            dct['data_type'] = dt
            dct['data_units'] = ut
            dct['enabled'] = True
            dct['full_name'] = fullname
            dct['index'] = index
            index += 1
            dct['instrument'] = None
            dct['label'] = unicode(label)
            dct['name'] = unicode(device)
            dct['ndim'] = 0
            dct['nexus_path'] = u''
            dct['normalization'] = 0
            dct['output'] = True
            dct['shape'] = shp

            if device in dontdisplay:
                dct['plot_axes'] = []
                dct['plot_type'] = 0
            elif dct['shape'] and len(dct['shape']) == 1:
                dct['plot_axes'] = ['<idx>']
                dct['plot_type'] = 1
            elif dct['shape'] and len(dct['shape']) == 2:
                dct['plot_axes'] = ['<idx>', '<idx>']
                dct['plot_type'] = 2
            else:
                dct['plot_axes'] = ['<mov>']
                dct['plot_type'] = 1

            dct['source'] = source
            ctrlChannels[fullname] = dct

        return index