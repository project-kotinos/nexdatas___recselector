#    "$Name:  $";
#    "$Header:  $";
# ============================================================================
#
# file :        TestMacroServer.py
#
# description : Python source for the TestMacroServer and its commands.
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                TestMacroServer are implemented in this file.
#
# project :     TANGO Device Server
#
# $Author:  $
#
# $Revision:  $
#
# $Log:  $
#
# copyleft :    European Synchrotron Radiation Facility
#               BP 220, Grenoble 38043
#               FRANCE
#
# ============================================================================
#          This file is generated by POGO
#    (Program Obviously used to Generate tango Object)
#
#         (c) - Software Engineering Group - ESRF
# ============================================================================
#


import PyTango
import sys
import pickle

# =================================================================
#   TestMacroServer Class Description:
#
#         My Simple Server
#
# =================================================================
#     Device States Description:
#
#   DevState.ON :  Server On
# =================================================================


class MacroServer(PyTango.Device_4Impl):

    # -------- Add you global variables here --------------------------

    # -----------------------------------------------------------------
    #    Device constructor
    # -----------------------------------------------------------------

    def __init__(self, cl, name):
        PyTango.Device_4Impl.__init__(self, cl, name)

        self.attr_value = ""
        MacroServer.init_device(self)
        self.attr_DoorList = ['doortestp09/testts/t1r228']

    # -----------------------------------------------------------------
    #    Device destructor
    # -----------------------------------------------------------------
    def delete_device(self):
        """ """

    # -----------------------------------------------------------------
    #    Device initialization
    # -----------------------------------------------------------------

    def init_device(self):
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())
        env = {'new': {'ActiveMntGrp': 'nxsmntgrp',
                       'DataCompressionRank': 0,
                       'NeXusSelectorDevice': u'p09/nxsrecselector/1',
                       'ScanDir': u'/tmp/',
                       'ScanFile': [u'sar4r.nxs'],
                       'ScanID': 192,
                       '_ViewOptions': {'ShowDial': True}}}

        self.attr_Environment = ("pickle", pickle.dumps(env))
        self.attr_DoorList = ['doortestp09/testts/t1r228']

    # -----------------------------------------------------------------
    #    Always excuted hook method
    # -----------------------------------------------------------------
    def always_executed_hook(self):
        pass

    # =================================================================
    #
    #    TestMacroServer read/write attribute methods
    #
    # =================================================================
    #
    # -----------------------------------------------------------------
    #    Read DoorList attribute
    # -----------------------------------------------------------------
    def read_DoorList(self, attr):
        #    Add your own code here

        attr.set_value(self.attr_DoorList or [])

    # -----------------------------------------------------------------
    #    Write DoorList attribute
    # -----------------------------------------------------------------
    def write_DoorList(self, attr):
        #    Add your own code here

        self.attr_DoorList = attr.get_write_value()

    # -----------------------------------------------------------------
    #    Read Environment attribute
    # -----------------------------------------------------------------
    def read_Environment(self, attr):
        #    Add your own code here

        attr.set_value(self.attr_Environment[0], self.attr_Environment[1])

    # -----------------------------------------------------------------
    #    Write Environment attribute
    # -----------------------------------------------------------------
    def write_Environment(self, attr):
        #    Add your own code here

        env = attr.get_write_value()
        envnew = {}
        envchange = {}
        envdel = []
        if env[0] == 'pickle':
            edict = pickle.loads(env[1])
            if 'new' in edict.keys():
                envnew = edict['new']
            if 'change' in edict.keys():
                envchange = edict['change']
            if 'del' in edict.keys():
                envdel = edict['del']
            envdict = pickle.loads(self.attr_Environment[1])
            if 'new' not in envdict.keys():
                envdict['new'] = {}
            newdict = envdict['new']
            newdict.update(envnew)
            newdict.update(envchange)
            for ed in envdel:
                if ed in newdict.keys():
                    newdict.pop(ed)
            self.attr_Environment = ("pickle", pickle.dumps(envdict))

    #
    # =================================================================
    #
    #    TestMacroServer command methods
    #
    # =================================================================
    #
    # -----------------------------------------------------------------
    #    SetState command:
    #
    #    Description: Set state of tango device
    #
    #    argin: DevString     tango state
    # -----------------------------------------------------------------
    def SetState(self, state):
        if state == "RUNNING":
            self.set_state(PyTango.DevState.RUNNING)
        elif state == "FAULT":
            self.set_state(PyTango.DevState.FAULT)
        elif state == "ALARM":
            self.set_state(PyTango.DevState.ALARM)
        else:
            self.set_state(PyTango.DevState.ON)


# =================================================================
#
#    MacroServerClass class definition
#
# =================================================================
class MacroServerClass(PyTango.DeviceClass):

    #    Class Properties
    class_property_list = {
    }

    #    Device Properties
    device_property_list = {
        'PoolNames':
            [PyTango.DevVarStringArray,
             "pool names",
             []],
    }

    #    Command definitions
    cmd_list = {
        'SetState':
            [[PyTango.DevString, "ScalarString"],
             [PyTango.DevVoid, ""]],
    }

    #    Attribute definitions
    attr_list = {
        'Environment':
            [[PyTango.DevEncoded,
              PyTango.SCALAR,
              PyTango.READ_WRITE],
             {
                 'description': "Environment attribute",
            }],
        'DoorList':
            [[PyTango.DevString,
              PyTango.SPECTRUM,
              PyTango.READ_WRITE,
              256],
             {
                 'description': "Environment attribute",
            }],
    }

# -----------------------------------------------------------------
#    MacroServerClass Constructor
# -----------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


# =================================================================
#   TestDoor Class Description:
#
#         My Simple Server
#
# =================================================================
#     Device States Description:
#
#   DevState.ON :  Server On
# =================================================================

class Door(PyTango.Device_4Impl):

    # -------- Add you global variables here --------------------------

    # -----------------------------------------------------------------
    #    Device constructor
    # -----------------------------------------------------------------

    def __init__(self, cl, name):
        PyTango.Device_4Impl.__init__(self, cl, name)

        self.attr_value = ""
        Door.init_device(self)

    # -----------------------------------------------------------------
    #    Device destructor
    # -----------------------------------------------------------------
    def delete_device(self):
            self.get_name()

    # -----------------------------------------------------------------
    #    Device initialization
    # -----------------------------------------------------------------
    def init_device(self):
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())

    # -----------------------------------------------------------------
    #    Always excuted hook method
    # -----------------------------------------------------------------
    def always_executed_hook(self):
        pass

    # =================================================================
    #
    #    TestDoor read/write attribute methods
    #
    # =================================================================
    #
    # =================================================================
    #
    #    TestDoor command methods
    #
    # =================================================================
    #
    # -----------------------------------------------------------------
    #    SetState command:
    #
    #    Description: Set state of tango device
    #
    #    argin: DevString     tango state
    # -----------------------------------------------------------------
    def SetState(self, state):
        if state == "RUNNING":
            self.set_state(PyTango.DevState.RUNNING)
        elif state == "FAULT":
            self.set_state(PyTango.DevState.FAULT)
        elif state == "ALARM":
            self.set_state(PyTango.DevState.ALARM)
        else:
            self.set_state(PyTango.DevState.ON)


# =================================================================
#
#    DoorClass class definition
#
# =================================================================
class DoorClass(PyTango.DeviceClass):

    #    Class Properties
    class_property_list = {
    }

    #    Device Properties
    device_property_list = {
    }

    #    Command definitions
    cmd_list = {
        'SetState':
            [[PyTango.DevString, "ScalarString"],
             [PyTango.DevVoid, ""]],
    }

    #    Attribute definitions
    attr_list = {
    }

# -----------------------------------------------------------------
#    DoorClass Constructor
# -----------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


# =================================================================
#
#    MacroServer class main method
#
# =================================================================
if __name__ == '__main__':
    try:
        argv = list(sys.argv)
        argv[0] = "MacroServer"
        py = PyTango.Util(argv)
        py.add_class(MacroServerClass, MacroServer)
        py.add_class(DoorClass, Door)

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed as e:
        print('-------> Received a DevFailed exception: %s' % e)
    except Exception as e:
        print('-------> An unforeseen exception occured.... %s' % e)
