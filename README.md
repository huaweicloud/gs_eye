# GS_EYE

#### Project Introduction
  This project is an monitor project for GaussDB(DWS) to collected affluent TIME SERIES target for maintainance analysis.


#### Soft Architecture



#### Installation

1. download this entire package to the cluster server
2. unzip the zipfile
3. run command: ./gs_metric.sh install
   App will be installed to the /home/omm/gs_metric as default


#### Usage

Before use this app, some softwares is needed.
0.1 apache/httpd: please install the httpd on the maintainance cluster, and be sure a path with the permission of put file by 'curl' from the production environment.
0.2 Python 2.7 or higher version is needed

Starting the agent
1. ./gs_metric.sh start --agent
Starting the server
2. ./gs_metric.sh start --server
Check status
3. ./gs_metric.sh status [--server | --agent]

#### Contributors

