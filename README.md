## Synopsis

This project is intended to be a replacement for pacemaker and various other fail-over cluster solutions that manages a DRBD filesystem. 

## Usage

```js
nighter@workstation:~/tmp/tmp/cluster-manager$ ./cluster

   _____         _
  / __| |_  _ __| |_ ___ _ _ 
 | (__| | || (_-<  _/ -_) '_|
  \___|_|\_,_/__/\__\___|_|  
                                                  
Usage: cluster [OPTIONS]

General Options

   status                                            Show cluster status.
   active           [--other_node_passive=False]     Set this node to active.
   passive          [--other_node_active=False]      Set this node to passive. 

Advanced Options

   heartbeat                                         Trigger heartbeat.
   heartbeat on     [--other_node_ha_enable=False]   Enable heartbeat.
   heartbeat off    [--other_node_ha_disable=False]  Disable heartbeat.
   heartbeat status                                  Show heartbeat status.

Optional Arguments

   --other_node_passive=False                        Opposite node will not automatic be set to passive.
   --other_node_active=False                         Opposite node will not automatic be set to active.
   --other_node_ha_disable=False                     Opposite node will not automatic set heartbeat to disabled.
   --other_node_ha_enable=False                      Opposite node will not automatic set heartbeat to enabled       
```


## Motivation

Needed a DRBD fail-over solution for OMD and Throughtworks Go on RHEL6 and pacemaker was not sufficient.

## Installation

First configure a DRBD filesystem.

Install dependencies.

```js
node1|node2 #  yum -y install git python-devel python-pip gcc
```

Install cluster-manager toolset.

```js
node1|node2 # useradd -m cluster
node1|node2 # echo "cluster" | passwd --stdin cluster
node1|node2 # su - cluster
node1|node2 $ git init
node1|node2 $ git remote add origin https://github.com/n1ght3r/cluster-manager.git 
node1|node2 $ git pull origin master
```

Install required python modules.

```js
node1|node2 # pip install -r /home/cluster/clusterlib/requirements.txt
```

Configure bash completion.

```js
node1|node2 # ln -s /home/cluster/clusterlib/bash_completion /etc/bash_completion.d/cluster
```

Cluster user need sudo support.

```js
node1|node2 # echo "cluster ALL=NOPASSWD:   ALL" | (EDITOR="tee -a" visudo)  
```
Note If you are concern of the security you can only add commands required by cluster manager toolset and not allow "ALL"


Edit config file on both nodes.

```js
node1|node2 $ vim ~/clusterlib/cluster.cfg
```

## API Reference

Framework consist of plugins to handle different applications. At the moment plugins exist for omd and Troughtworks Go.
Look at the other plugins to mimic the structure and create your own plugin if your application is not covered.   

```js
node1|node2 $ cat ~/clusterlib/plugins/omd.py
```

## Contributors

Feel free to contribute. 

## License

Apache Software License 1.1
