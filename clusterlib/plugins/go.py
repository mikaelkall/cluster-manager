#!/usr/bin/env python
from yapsy.IPlugin import IPlugin
import datetime
import commands
import time
import sys
from clusterlib.clusterlib import *

class Go(IPlugin):

    def __init__(self):

	# Hardcoded settings.
	self.settings = {'mountpoint': '/home/go'}; 

    def get_plugin_settings(self):
	return self.settings 


    def service_start(self):
        status, output = commands.getstatusoutput("sudo /home/go/etc/init.d/go-server start")
        if self.service_status() == True:
            clusterlib().logprint("I","%s -- GO started successfully." % clusterlib().get_this_node_address())
        else:
            clusterlib().logprint("W","%s -- GO did not start." % clusterlib().get_this_node_address())


    def service_stop(self):
        status, output = commands.getstatusoutput("sudo /home/go/etc/init.d/go-server stop")
        if self.service_status() == False:
            clusterlib().logprint("I","%s -- GO stopped successfully." % clusterlib().get_this_node_address())
        else:
            clusterlib().logprint("W","%s -- GO did not stop." % clusterlib().get_this_node_address())


    def service_status(self):
        status, output = commands.getstatusoutput("sudo /home/go/etc/init.d/go-server status")
        x = [row for row in output.split("\n") if "Go Server is running." in row]
        if len(x) == 1:
            return True
        else:
            return False


    def check_ha(self):
        output = clusterlib().other_node_execute("sudo /home/go/etc/init.d/go-server status")
        x = [row for row in output.split("\n") if "running" in row]
        if len(x) == 6:
            return True
        else:
            return False
