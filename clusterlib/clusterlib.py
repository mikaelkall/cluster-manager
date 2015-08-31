#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
  DRBD Cluster Solution. 
  Copyright (C) 2015 Mikael Kall.
  This script manages a failover solution with DRBD.  
"""
__author__ = 'kall.micke@gmail.com'

from ConfigParser import SafeConfigParser
from crontab import CronTab
from socket import gethostname; 
from fabric.api import *
from fabric.operations import local,put,sys
from fabric.contrib.files import exists
from yapsy.PluginManager import PluginManager
import commands
import signal
import socket
import datetime
import time
import sys
import os
import re


class clusterlib:

    def __init__(self):

	config = self.__load_settings()
	for key, value in dict(config.items('cluster')).iteritems():
	    setattr(self, str(key), str(value))

        # Defaults to omd if no plugin defined.
        plugin_name=(self.load_plugin if hasattr(self,'load_plugin') else 'omd')

        # Load plugins
        manager = PluginManager()
        manager.setPluginPlaces(["/home/cluster/clusterlib/plugins"])
        manager.collectPlugins()

        # Expose plugin.
        self.plugin = manager.getPluginByName(plugin_name, category='Default')


    def heartbeat(self):

	# Only run if heartbeat is enable
        try: 
	    if bool(self.heartbeat_enabled) == False:
	        return
	except:
		return

	# Only continue from here if we are passive node.
	if self.__check_active_passive(False) == True:
	    if self.__check_active_passive_by_command() == True:
		self.__remove_ha_lockfile()
	        return

        if self.plugin.plugin_object.check_ha() == False:
	    if os.path.isfile('/tmp/heartbeat.lock') == False:	        	    
	        self.__create_ha_lockfile()
		return
	
	    file_mod_time = os.stat('/tmp/heartbeat.lock').st_mtime
	    last_time = (time.time() - file_mod_time) / 60
	    if last_time > 7:
	        self.logprint("E"," -- Prevents looping giving up.")
		return
	    elif last_time > 0.4:
		self.active()
	else:
	    self.__remove_ha_lockfile()


    def __create_ha_lockfile(self):
    	with open('/tmp/heartbeat.lock','w') as lockfile:
            pass


    def __remove_ha_lockfile(self):
        if os.path.isfile('/tmp/heartbeat.lock') == True: 
	    os.remove('/tmp/heartbeat.lock')


    def __check_ha_tcp(self, port = 5000):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(1)
	result = sock.connect_ex((self.vip_address, port))
        if result == 0:
            return True
        else:
            return False


    def status(self):

        other_node_address = self.get_other_node_address()
	this_node_address = self.get_this_node_address()

	print ""	
 	if self.__check_active_passive_by_address(this_node_address, False) == True:
	    print("%s : %s" % ( this_node_address, Color().Green("Active [*]")))
	else:
	    print("%s : %s" % ( this_node_address, Color().Red("Passive [*]") ))

	if self.__check_active_passive_by_address(other_node_address, False) == True:
	    print("%s : %s" % ( other_node_address, Color().Green("Active" ) ))
	else:
	    print("%s : %s" % ( other_node_address, Color().Red("Passive") ))	    
	print ""

 
    def heartbeat_status(self):

        other_node_address = self.get_other_node_address()
        this_node_address = self.get_this_node_address()
	
	if self.__check_heartbeat_cron_status(this_node_address) == True:
	    print("%s : %s" % ( this_node_address, Color().Green("[Heartbeat Enabled]")))	
	else:
	    print("%s : %s" % ( this_node_address, Color().Red("[Heartbeat Disabled]") ))
	
        if self.__check_heartbeat_cron_status(other_node_address) == True:
            print("%s : %s" % ( other_node_address, Color().Green("[Heartbeat Enabled]")))
        else:
            print("%s : %s" % ( other_node_address, Color().Red("[Heartbeat Disabled]") ))

	
    def __check_heartbeat_cron_status(self, address):

	if address == self.get_this_node_address():
            status, output = commands.getstatusoutput('crontab -l')
	else:
	    if [row for row in self.other_node_execute("crontab -l", False).split('\n') if not row.startswith('#') and "heartbeat" in row]:
	        return True
	    else:
		return False

        if [row for row in output.split('\n') if not row.startswith('#') and "heartbeat" in row]:
	    return True
	else:
	    return False
	

    def active(self, other_node_down = True):

        if self.__check_active_passive(False) == True:
            address = self.get_this_node_address()
            self.logprint("I","%s: is already active." % ( address ))
            return

        other_node_address = self.get_other_node_address()
        if self.__check_node_connection(other_node_address) == False:
             self.logprint("W","active node: %s is unreachable." % ( env.host_string ))

        self.__check_remote_permissions()
        self.__check_local_permissions()

        if other_node_down == True:
            self.__make_other_node_passive()

	self.__enable_vip()
	self.__make_node_active()
        self.plugin.plugin_object.service_start()


    def passive(self, other_node_up = True):

        if self.__check_active_passive(False) == False:
	    address = self.get_this_node_address()
	    self.logprint("I","%s: is already passive." % ( address ))
	    return

        other_node_address = self.get_other_node_address()
        if self.__check_node_connection(other_node_address) == False:
             self.logprint("W","Failed to swith to passive since active node: %s is unreachable." % ( env.host_string )) 
	     sys.exit(1)

	self.__check_remote_permissions()
	self.__check_local_permissions()

        self.plugin.plugin_object.service_stop()

	self.__make_node_passive()
	self.__disable_vip()
	
	if other_node_up == True:
	    self.__make_other_node_active()		
	
		
    def sanity_check(self):
	print "sanity check"

    def __make_other_node_active(self):
        output = self.other_node_execute("~/cluster active --other_node_passive=False", False)
	print output


    def __make_other_node_passive(self):
        output = self.other_node_execute("~/cluster passive --other_node_active=False", False)
        print output


    def other_node_execute(self, command, use_sudo = True):
        env.host_string = self.get_other_node_address()
        env.output_prefix = False
        env.user = self.username
        env.password = self.password
        output=""
        with hide('everything','stderr'):
            with cd("/"):
                if use_sudo == True:
                    try:
                        output=sudo(command.strip())
                    except:
                        pass
                else:
                    try:
                        output=run(command.strip())
                    except:
                        pass
                return output


    def __make_node_passive(self):

	if self.__check_active_passive(False) == False:
	    return

	address = self.get_this_node_address()

	status, output = commands.getstatusoutput('df /dev/drbd0')
	if "drbd0" not in output:
	    self.logprint("W","%s: drbd0 was not mounted." % address)
	else:
	    try:
	        plugin_settings = self.plugin.plugin_object.get_plugin_settings()
	        self.umount(plugin_settings['mountpoint'])
	    except:
		self.logprint("E","%s -- Failed to unmount, be sure mount point is set in plugin." % address)		

	status, output = commands.getstatusoutput('sudo drbdadm secondary clusterdb')
	if status != 0:
	     self.logprint("W","%s -- Failed to switch to passive." % address)
	     return

	self.logprint("I","%s -- Switched to passive." % address)

 
    def umount(self, directory):

	if not directory:
	    return

	status, output = commands.getstatusoutput("sudo umount %s" % directory)
	if status != 0:
	    self.logprint("W","%s -- Umount failed on %s since a process holds mount point." % ( self.get_this_node_address(), directory ))
	    output = str(commands.getoutput("sudo lsof +D %s |awk '{print $2}'" % directory)).split("\n")
	    if output[0] == "PID":
		output.pop(0)
		for pid in output:
		    os.system("sudo kill -9 %s" % (int(pid)))
		    self.logprint("W"," -- Killed pid: %s" % ( pid ))

	    status, output = commands.getstatusoutput("sudo umount %s" % directory)
            if status != 0:
                self.logprint("W","%s -- Failed to umount %s" % ( self.get_this_node_address(), directory ))


    def __make_node_active(self):

        address = self.get_this_node_address()

        status, output = commands.getstatusoutput('sudo drbdadm primary clusterdb')
        if status != 0:
             self.logprint("W","%s -- Failed to switch to active." % address)
             return

        status, output = commands.getstatusoutput('df /dev/drbd0')
	if "drbd0" in output:
            self.logprint("W","%s: drbd0 was already mounted." % address)
        else:
	    try:
                plugin_settings = self.plugin.plugin_object.get_plugin_settings()
            except:
                self.logprint("E","%s -- Failed to unmount, be sure mount point is set in plugin." % address)
		return

            status, output = commands.getstatusoutput("sudo mount /dev/drbd0 %s" % ( plugin_settings['mountpoint'] ))
            if status != 0:
                self.logprint("W","%s -- Failed to mount %s" % ( address, plugin_settings['mountpoint'] ))
		return	

	self.logprint("I","%s -- Switched to active." % address)


    def get_other_node_address(self):
        if int(self.id) == 1:
            address = self.node2
        elif int(self.id) == 2:
            address = self.node1
        else:
            self.logprint("W"," -- Can't find a id on this node.")
            return

        return address


    def get_this_node_address(self):
        if int(self.id) == 1:
            address = self.node1
        elif int(self.id) == 2:
            address = self.node2
        else:
            self.logprint("W"," -- Can't find a id on this node.")
            return

        return address


    def __check_local_permissions(self):
	 status, output = commands.getstatusoutput('sudo whoami')
	 if status != 0:
	     self.logprint("E"," -- sudo access is reguired to control the cluster resource.")
	     sys.exit(1) 

         if output != "root":
             self.logprint("E"," -- Missing required permissions.")
             sys.exit(1)


    def __check_remote_permissions(self):
	output = self.other_node_execute('whoami')
        if output != "root":
            self.logprint("W"," -- Missing required permission on: %s" % ( env.host_string ))
            return


    def __check_node_connection(self, address, verbose = True):
        try:
            s = socket.socket()
            s.settimeout(3)	
	    s.connect((address, 22))
	    if verbose == True:
	        self.logprint("I","%s -- Connection successful." % (address))
	    return True
	except Exception, e:
	    if verbose == True:
	        self.logprint("I","%s -- Connection failed." % (address))
	    return False


    def __check_active_passive_by_command(self, verbose = True):
	status, output = commands.getstatusoutput('sudo drbdadm role clusterdb')
	if output[0:7] == "Primary":
	    return True
	else:
	    return False


    def __check_active_passive(self, verbose = True):
	drbd_proc_file="/proc/drbd"
        if os.path.isfile(drbd_proc_file) == False:	
	    self.logprint("E","Failed to retrieve cluster status.")
	    return

	with open(drbd_proc_file) as drbd:
	    x = [row for row in drbd.readlines() if "0: cs:Connected ro:" in row]
	    if not x:
	        self.logprint("E"," -- Failed to retrieve cluster status.")
		return

	    if bool(re.findall("Primary\/Secondary", str(x[0]).strip())) == True:
		if verbose == True:
		    self.logprint("I","%s : Active" % gethostname())
		return True
	    elif bool(re.findall("Secondary\/Primary", str(x[0]).strip())) == True:
		if verbose == True:
	            self.logprint("I","%s : Passive" % gethostname())
		return False
	    else:
		if verbose == True:
		    self.logprint("I","%s : Unknown" % gethostname())
		return False

	
    def __check_active_passive_by_address(self, address, verbose = True):

	if address == self.get_this_node_address(): 
            drbd_proc_file="/proc/drbd"
    
            if os.path.isfile(drbd_proc_file) == False:
                self.logprint("E","%s -- Failed to retrieve cluster status." % address)
                return

            with open(drbd_proc_file) as drbd:
                x = [row for row in drbd.readlines() if "0: cs:Connected ro:" in row]
	else:
	    x = [row for row in self.other_node_execute("cat /proc/drbd").split('\r\n') if "0: cs:Connected ro:" in row]

        if not x:
            if verbose == True:
                self.logprint("I","%s : Unknown" % address)
            return False

        if bool(re.findall("Primary\/Secondary", str(x[0]).strip())) == True:
            if verbose == True:
                self.logprint("I","%s : Active" % address)
            return True
        elif bool(re.findall("Secondary\/Primary", str(x[0]).strip())) == True:
            if verbose == True:
                self.logprint("I","%s : Passive" % address)
            return False
        else:
            if verbose == True:
                self.logprint("I","%s : Unknown" % address)
            return False


    def logprint(self, type, message):
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        if bool(self.logfile_enabled) == True:
            path = os.path.dirname(os.path.abspath(__file__))
            if not os.path.isdir("%s/../log" % (path)):
                os.makedirs("%s/../log" % (path))
            logfile = "%s/../log/cluster.log" % path
            with open(logfile,'a') as logfile:
                logfile.write("%s [%s] -- %s \n" % (st, type, message))
        print("%s [%s] -- %s " % (st, type, message))


    def __load_settings(self):
	config = SafeConfigParser()
	path = os.path.dirname(os.path.abspath(__file__))
	filename = "%s/cluster.cfg" % path
	if os.path.isfile(filename) == False:
	    self.logprint("E"," -- Can't find config: %s" % (filename))
	    sys.exit(1)

	config.read(filename)
	return config


    def __enable_vip(self):

	if not hasattr(self, 'vip_device') or not hasattr(self, 'vip_address'):
	    self.logprint("E","%s -- Required vip_device and vip_address is missing in config file, can't use vip." % self.get_this_node_address())
	    sys.exit(1)	

	self.logprint("I","%s -- Configures virtual address: %s " % ( self.get_this_node_address(), self.vip_address ))
	status, output = commands.getstatusoutput("sudo ifconfig %s %s netmask 255.255.255.0" % ( self.vip_device, self.vip_address )) 

 
    def __disable_vip(self):

        if not hasattr(self, 'vip_device') or not hasattr(self, 'vip_address'):
            self.logprint("E","%s -- Required vip_device and vip_address is missing in config file, can't use vip." % self.get_this_node_address())       
            sys.exit(1)

	self.logprint("I","%s -- Disables vip device: %s " % ( self.get_this_node_address(), self.vip_device ))
	status, output = commands.getstatusoutput("sudo ifconfig %s down" % ( self.vip_device ))


    def enable_ha_cronjob(self, other_node_ha_enable = True):
        cron = CronTab()
        job = cron.new(command='/home/cluster/cluster heartbeat > /dev/null 2>&1')
        job.minute.every(1)
        job.set_comment("heartbeat")
        job.enable()
        cron.write()

	if other_node_ha_enable == True:
	    output = self.other_node_execute("~/cluster heartbeat on --other_node_ha_enable=False", False)
	    self.logprint("I","%s -- Heartbeat enabled. " % ( self.get_other_node_address()))

	self.logprint("I","%s -- Heartbeat enabled. " % ( self.get_this_node_address()))
	

    def disable_ha_cronjob(self, other_node_ha_disable = True):
       cron = CronTab()
       cron.remove_all('/home/cluster/cluster heartbeat > /dev/null 2>&1')
       cron.write()

       if other_node_ha_disable == True:
            output = self.other_node_execute("~/cluster heartbeat off --other_node_ha_disable=False", False)
	    self.logprint("I","%s -- Heartbeat disabled. " % ( self.get_other_node_address()))

       self.logprint("I","%s -- Heartbeat disabled. " % ( self.get_this_node_address()))


class Color:
    """
    Color class
    Writes output in colors.
    """
    def __init__(self):
        # Colors
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.ENDC = '\033[0m'
        self.BOLD = "\033[1m"

    def Green(self,msg):
        return self.GREEN + msg + self.ENDC

    def Yellow(self,msg):
        return self.YELLOW + msg + self.ENDC

    def Red(self,msg):
        return self.RED + msg + self.ENDC

	
if __name__ == "__main__":  
    pass
