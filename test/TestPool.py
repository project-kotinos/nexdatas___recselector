#    "$Name:  $";
#    "$Header:  $";
# ============================================================================
#
# file :        TestPool.py
#
# description : Python source for the TestPool and its commands.
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                TestPool are implemented in this file.
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
import json
import TestMGSetUp

# =================================================================
#   TestPool Class Description:
#
#         My Simple Server
#
# =================================================================
#     Device States Description:
#
#   DevState.ON :  Server On
# =================================================================


class Pool(PyTango.Device_4Impl):

    # -------- Add you global variables here --------------------------

    # -----------------------------------------------------------------
    #    Device constructor
    # -----------------------------------------------------------------

    def __init__(self, cl, name):
        PyTango.Device_4Impl.__init__(self, cl, name)

        self.attr_value = ""
        self.attr_AcqChannelList = []
        self.attr_MeasurementGroupList = []
        self.attr_ExpChannelList = []
        self.attr_MotorList = []
        self._tmgs = []
        Pool.init_device(self)

    # -----------------------------------------------------------------
    #    Device destructor
    # -----------------------------------------------------------------
    def delete_device(self):
        for tmg in self._tmgs:
            tmg.tearDown()

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

    #
    # =================================================================
    #
    #    TestPool read/write attribute methods
    #
    # =================================================================
    #
    # -----------------------------------------------------------------
    #    Read AcqChannelList attribute
    # -----------------------------------------------------------------
    def read_AcqChannelList(self, attr):
        attr.set_value(self.attr_AcqChannelList)

    # -----------------------------------------------------------------
    #    Write AcqChannelList attribute
    # -----------------------------------------------------------------
    def write_AcqChannelList(self, attr):
        self.attr_AcqChannelList = attr.get_write_value() or []

    # -----------------------------------------------------------------
    #    Read MeasurementGroupList attribute
    # -----------------------------------------------------------------
    def read_MeasurementGroupList(self, attr):
        attr.set_value(self.attr_MeasurementGroupList)

    # -----------------------------------------------------------------
    #    Write MeasurementGroupList attribute
    # -----------------------------------------------------------------
    def write_MeasurementGroupList(self, attr):
        self.attr_MeasurementGroupList = attr.get_write_value() or []

    # -----------------------------------------------------------------
    #    Read ExpChannelList attribute
    # -----------------------------------------------------------------
    def read_ExpChannelList(self, attr):
        attr.set_value(self.attr_ExpChannelList)

    # -----------------------------------------------------------------
    #    Write ExpChannelList attribute
    # -----------------------------------------------------------------
    def write_ExpChannelList(self, attr):
        self.attr_ExpChannelList = attr.get_write_value() or []

    # -----------------------------------------------------------------
    #    Read MotorList attribute
    # -----------------------------------------------------------------
    def read_MotorList(self, attr):
        attr.set_value(self.attr_MotorList)

    # -----------------------------------------------------------------
    #    Write MotorList attribute
    # -----------------------------------------------------------------
    def write_MotorList(self, attr):
        self.attr_MotorList = attr.get_write_value() or []

    # =================================================================
    #
    #    TestPool command methods
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

    # -----------------------------------------------------------------
    #    DeleteElement command:
    #
    #    Description: Set state of tango device
    #
    #    argin: DevString     element
    # -----------------------------------------------------------------
    def DeleteElement(self, name):
        attrs = [
            "attr_MeasurementGroupList",
            "attr_AcqChannelList",
            "attr_ExpChannelList",
            "attr_MotorList"
        ]
        for attr in attrs:
            inlist = list(getattr(self, attr))
            outlist = []
            for elem in inlist:
                el = json.loads(elem)
                if 'name' not in el or name != el['name']:
                    outlist.append(elem)
            getattr(self, attr)[:] = outlist

    # -----------------------------------------------------------------
    #    CreateMeasurementGroup command:
    #
    #    Description: Set state of tango device
    #
    #    argin: DevVarStringArray     element
    # -----------------------------------------------------------------
    def CreateMeasurementGroup(self, names):
        mg = names[0]
        # tm = names[1]
        self.attr_MeasurementGroupList.append(json.dumps(
            {"name": mg,
             "full_name": "mntgrp/pool/%s" % (mg)}))
        tmg = TestMGSetUp.TestMeasurementGroupSetUp(name=mg)
        tmg.setUp()
        self._tmgs.append(tmg)


# =================================================================
#
#    PoolClass class definition
#
# =================================================================
class PoolClass(PyTango.DeviceClass):

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
        'DeleteElement':
            [[PyTango.DevString, "element name"],
             [PyTango.DevVoid, ""]],
        'CreateMeasurementGroup':
            [[PyTango.DevVarStringArray, "channel names"],
             [PyTango.DevVoid, ""]],
    }

    #    Attribute definitions
    attr_list = {
        'AcqChannelList':
            [[PyTango.DevString,
              PyTango.SPECTRUM,
              PyTango.READ_WRITE, 4096],
             {
                 'label': "",
                 'description': " "
            }],
        'MeasurementGroupList':
            [[PyTango.DevString,
              PyTango.SPECTRUM,
              PyTango.READ_WRITE, 4096],
             {
                 'label': "",
                 'description': " "
            }],
        'ExpChannelList':
            [[PyTango.DevString,
              PyTango.SPECTRUM,
              PyTango.READ_WRITE, 4096],
             {
                 'label': "",
                 'description': " "
            }],
        'MotorList':
            [[PyTango.DevString,
              PyTango.SPECTRUM,
              PyTango.READ_WRITE, 4096],
             {
                 'label': "",
                 'description': " "
            }],
    }

    # -----------------------------------------------------------------
    #    PoolClass Constructor
    # -----------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)
        # print "In TestPoolClass  constructor"


# =================================================================
#
#    Pool class main method
#
# =================================================================
if __name__ == '__main__':
    try:
        argv = list(sys.argv)
        argv[0] = "Pool"
        py = PyTango.Util(argv)
        py.add_class(PoolClass, Pool)

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed as e:
        print('-------> Received a DevFailed exception: %s' % e)
    except Exception as e:
        print('-------> An unforeseen exception occured.... %s' % e)
