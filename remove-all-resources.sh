#!/bin/bash

CLUSTER_NAME=$1
export OS_CLOUD=psi-pipelines

if [ -z $CLUSTER_NAME ]; then
  echo "specify cluster name as a parameter of this script"
  exit 1
fi
echo -e "Cluster name: $CLUSTER_NAME\n"
echo "========================================================================="
echo "| Clusters should be removed using the script destroy-cluster.sh.       |"
echo "| This script is dangerous, run it only if you know what you are doing! |"
echo "========================================================================="

read -r -n 1 -p "Do you want to continue? (Yy|Nn) " REPLY
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  rm -rf "cluster/$CLUSTER_NAME"
else
  exit 4
fi

echo

for RESOURCE_TYPE in server "network trunk" volume; do
  echo --- $RESOURCE_TYPE
  ITEMS=`openstack $RESOURCE_TYPE list -f value -c Name | grep $CLUSTER_NAME`
  for ITEM in $ITEMS; do
    openstack $RESOURCE_TYPE delete $ITEM
  done
done

echo --- container
ITEMS=`openstack container list -f value -c Name | grep $CLUSTER_NAME`
for ITEM in $ITEMS; do
  openstack container delete --recursive $ITEM
done

echo --- clear router gateway
ROUTER=`openstack router list -f value -c Name | grep $CLUSTER_NAME`
openstack router unset --external-gateway $ROUTER
#PORT=`openstack router show $ROUTER -f json | jq -r .interfaces_info | jq -r .[0].port_id`
#openstack router remove port $ROUTER $PORT

SUBNET=`openstack subnet list -f value -c Name | grep $CLUSTER_NAME`

echo --- removing subnet from router
openstack router remove subnet $ROUTER $SUBNET

echo --- removing ports
NET=`openstack network list -f value -c Name | grep $CLUSTER_NAME`
ITEMS=`openstack port list --network $NET -f value -c ID`
#ITEMS=`openstack port list --router $ROUTER -f value -c ID`
#echo --- port
for ITEM in $ITEMS; do
  openstack port delete $ITEM
done

for RESOURCE_TYPE in router "security group" subnet network; do
  echo --- $RESOURCE_TYPE
  ITEMS=`openstack $RESOURCE_TYPE list -f value -c Name | grep $CLUSTER_NAME`
  for ITEM in $ITEMS; do
    openstack $RESOURCE_TYPE delete $ITEM
  done
done

ITEMS=`openstack floating ip list --long -f value -c 'Floating IP Address' -c Description | grep $CLUSTER_NAME`
echo --- floating IP
for ITEM in $ITEMS; do
  openstack floating ip delete $ITEM
done
