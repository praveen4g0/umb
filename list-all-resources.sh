#!/bin/bash

CLUSTER_NAME=$1
export OS_CLOUD=${OS_CLOUD:-"psi-gitops"}

if [ -z $CLUSTER_NAME ]; then
  echo "specify cluster name as a parameter of this script"
  exit 1
fi
echo cluster name: $CLUSTER_NAME

echo --- object containers
openstack container list -f value -c Name | grep $CLUSTER_NAME

echo --- instances
openstack server list -f value -c Name | grep $CLUSTER_NAME

echo --- trunks
openstack network trunk list -f value -c Name | grep $CLUSTER_NAME

echo --- ports
openstack port list -f value -c Name | grep $CLUSTER_NAME

echo --- router
openstack router list -f value -c Name | grep $CLUSTER_NAME

echo --- subnets
openstack subnet list -f value -c Name | grep $CLUSTER_NAME

echo --- networks
openstack network list -f value -c Name | grep $CLUSTER_NAME

echo --- security groups
openstack security group list -f value -c Name | grep $CLUSTER_NAME

echo --- volumes
openstack volume list -f value -c Name | grep $CLUSTER_NAME

echo --- floating IPs
openstack floating ip list --long -f value -c 'Floating IP Address' -c Description | grep $CLUSTER_NAME


