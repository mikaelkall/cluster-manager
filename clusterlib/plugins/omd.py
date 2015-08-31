#!/usr/bin/env python
from yapsy.IPlugin import IPlugin
import datetime
import commands
import time
import sys
from clusterlib.clusterlib import *

class Omd(IPlugin):

    def __init__(self):
        self.settings = {'mountpoint':'/opt/omd'};


    def get_plugin_settings(self):
        return self.settings


    def service_start(self):
        site=(clusterlib().site if hasattr(clusterlib(),'site') else 'prod')
        status, output = commands.getstatusoutput("sudo /usr/bin/omd start %s" % ( site ))
        if self.service_status() == True:
            clusterlib().logprint("I","%s -- OMD started successfully." % clusterlib().get_this_node_address())
        else:
            clusterlib().logprint("W","%s -- All OMD services did not start." % clusterlib().get_this_node_address())


    def service_stop(self):

        site=(clusterlib().site if hasattr(clusterlib(),'site') else 'prod')
        status, output = commands.getstatusoutput("sudo /usr/bin/omd stop %s" % ( site ))
        if self.service_status() == False:
            clusterlib().logprint("I","%s -- OMD stopped successfully." % clusterlib().get_this_node_address())
        else:
            clusterlib().logprint("W","%s -- All OMD services did not stop." % clusterlib().get_this_node_address())

	clusterlib().umount("/opt/omd/sites/%s/tmp" % ( site ))


    def service_status(self):
        site=(clusterlib().site if hasattr(clusterlib(),'site') else 'prod')
        status, output = commands.getstatusoutput("sudo /usr/bin/omd status %s" % ( site ))
        x = [row for row in output.split("\n") if "running" in row]
        if len(x) == 6:
            return True
        else:
            return False


    def check_ha(self):
        site=(clusterlib().site if hasattr(clusterlib(),'site') else 'prod')
        output = clusterlib().other_node_execute("sudo /usr/bin/omd status %s" % ( site ))
        x = [row for row in output.split("\n") if "running" in row]
        if len(x) == 6:
            return True
        else:
            return False
