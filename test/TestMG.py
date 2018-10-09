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

# =================================================================
#   TestMeasurementGroup Class Description:
#
#         My Simple Server
#
# =================================================================
#     Device States Description:
#
#   DevState.ON :  Server On
# =================================================================


class MeasurementGroup(PyTango.Device_4Impl):

    # -------- Add you global variables here --------------------------

    # -----------------------------------------------------------------
    #    Device constructor
    # -----------------------------------------------------------------

    def __init__(self, cl, name):
        PyTango.Device_4Impl.__init__(self, cl, name)

        self.attr_value = ""
        self.attr_Configuration = "{}"
        MeasurementGroup.init_device(self)

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

    # -----------------------------------------------------------------
    #    Always excuted hook method
    # -----------------------------------------------------------------
    def always_executed_hook(self):
        pass

    #
    # =================================================================
    #
    #    TestMeasurementGroup read/write attribute methods
    #
    # =================================================================
    #
    # -----------------------------------------------------------------
    #    Read Configuration attribute
    # -----------------------------------------------------------------
    def read_Configuration(self, attr):
        attr.set_value(self.attr_Configuration)

    # -----------------------------------------------------------------
    #    Write Configuration attribute
    # -----------------------------------------------------------------
    def write_Configuration(self, attr):
        self.attr_Configuration = attr.get_write_value() or ""

    # =================================================================
    #
    #    TestMeasurementGroup command methods
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
#    MeasurementGroupClass class definition
#
# =================================================================
class MeasurementGroupClass(PyTango.DeviceClass):

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
        'Configuration':
            [[PyTango.DevString,
              PyTango.SCALAR,
              PyTango.READ_WRITE],
             {
                 'label': "",
                 'description': " "
            }],
    }

# -----------------------------------------------------------------
#    MeasurementGroupClass Constructor
# -----------------------------------------------------------------
    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


# =================================================================
#
#    MeasurementGroup class main method
#
# =================================================================
if __name__ == '__main__':
    try:
        argv = list(sys.argv)
        argv[0] = "MeasurementGroup"
        py = PyTango.Util(argv)
        py.add_class(MeasurementGroupClass, MeasurementGroup)

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed as e:
        print('-------> Received a DevFailed exception: %s' % e)
    except Exception as e:
        print('-------> An unforeseen exception occured.... %s' % e)
