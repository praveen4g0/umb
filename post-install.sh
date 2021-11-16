#!/bin/bash

export AWS_PROFILE=${AWS_PROFILE:-"aws-gitops"}
CLUSTER_NAME=$1
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
DOMAIN=$(jq -r '.base_domain' "cluster/$CLUSTER_NAME/terraform.tfvars.json")
NETWORK=$(jq -r '."*installconfig.InstallConfig".config.platform.openstack.externalNetwork' "cluster/$CLUSTER_NAME/.openshift_install_state.json")
export OS_CLOUD=${OS_CLOUD:-"psi-gitops"}

if [ -z $CLUSTER_NAME ]; then
  echo -e "Specify desired cluster name as a parameter of this script \n"
  echo "Usage:"
  echo "  $0 [name]"
  exit 1
fi

echo "Allocating a floating IP for cluster's ingress"
INGRESS_PORT=$(openstack port list -f value -c Name | grep $CLUSTER_NAME- |  grep ingress-port)
FIP=$(openstack floating ip create --description "$CLUSTER_NAME-ingress" -f value -c floating_ip_address --port $INGRESS_PORT $NETWORK)
if [ $? != 0 ]; then
  echo "Failed to allocate a floating IP for ingress"
  exit 10
fi

echo "Getting zone ID in Route53"
ZONES=$(aws route53 list-hosted-zones --output json)
ZONE_ID=$(echo $ZONES | jq -r ".HostedZones[] | select(.Name==\"$DOMAIN.\") | .Id")

if [ -z $ZONE_ID ]; then
  echo "Domain $DOMAIN not found in Route53"
  exit 20
fi

echo "Updating DNS records in Route53"
RESPONSE=$(aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch '{ "Comment": "Update A record for cluster API", "Changes": [ { "Action": "CREATE", "ResourceRecordSet": { "Name": "*.apps.'$CLUSTER_NAME'.'$DOMAIN'", "Type": "A", "TTL":  60, "ResourceRecords": [ { "Value": "'$FIP'" } ] } } ] }' --output json)
if [ $? != 0 ]; then
  echo "Failed to update A record for cluster"
  echo "Releasing previously allocated floating IP"
  openstack floating ip delete $FIP
  exit 25
fi

echo "Waiting for DNS change to propagate"
aws route53 wait resource-record-sets-changed --id $(echo $RESPONSE | jq -r '.ChangeInfo.Id')

echo "Logging in to cluster $CLUSTER_NAME as kubeadmin"
export KUBECONFIG=$DIR/cluster/$CLUSTER_NAME/auth/kubeconfig


sleep 10

APISERVER=$(oc config view --minify -o jsonpath='{.clusters[0].cluster.server}')
echo "Login into PSI cluster using this command: 'oc login -u kubeadmin -p $(cat $DIR/cluster/$CLUSTER_NAME/auth/kubeadmin-password) $APISERVER --insecure-skip-tls-verify=true'"

# Sometime the url can let us down, so let's add a counter
i=1
while [[ $i -le 10 ]];do
  oc login -u kubeadmin -p $(cat $DIR/cluster/$CLUSTER_NAME/auth/kubeadmin-password) $APISERVER --insecure-skip-tls-verify=true && break
  sleep 5
  (( i++ ))
done
