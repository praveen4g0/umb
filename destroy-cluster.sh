#!/bin/bash

#set -e

export AWS_PROFILE=${AWS_PROFILE:-"aws-gitops"}
CLUSTER_NAME=$1
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
export OS_CLOUD=${OS_CLOUD:-"psi-gitops"}

if [ -z $CLUSTER_NAME ]; then
  echo -e "Specify desired cluster name as a parameter of this script \n"
  echo "Usage:"
  echo "  $0 [name]"
  exit 1
fi

if [ -f cluster/$CLUSTER_NAME/.openshift_install_state.json ]; then
  # installation got quite far
  DOMAIN=$(jq -r '."*installconfig.InstallConfig".config.baseDomain' cluster/$CLUSTER_NAME/.openshift_install_state.json)
else
  # installation probably did not start
  DOMAIN=$(yq -r '.baseDomain' cluster/$CLUSTER_NAME/install-config.yaml)
fi

if [ -z $CLUSTER_NAME ]; then
  echo -e "Specify desired cluster name as a parameter of this script \n"
  echo "Usage:"
  echo "  $0 [name]"
  exit 1
fi
echo "Cluster name: $CLUSTER_NAME"

if [ ! -f "$HOME/.config/openstack/secure.yaml" ] && [ ! -f "/etc/openstack/secure.yaml" ]; then
  echo -n "File secure.yaml not found. See "
  echo "https://docs.openstack.org/openstacksdk/latest/user/config/configuration.html#config-files for more info."
  exit 2
fi

if [ ! -d "cluster/$CLUSTER_NAME" ]; then
  echo "Directory \"cluster/$CLUSTER_NAME\" does not exist."
  exit 3
fi

# if destroy script is invoked immediately after prepare script, it is not possible/necessary to destroy cluster
if [ -f "cluster/$CLUSTER_NAME/metadata.json" ]; then
  echo "Running \"openshift-install destroy cluster\""
  openshift-install --dir=cluster/$CLUSTER_NAME --log-level debug destroy cluster
fi

if [ $? != 0 ]; then
  echo "Failed to destroy cluster, try to run the script again."
  exit 4
fi

echo "Getting zone ID in Route53"
ZONES=$(aws route53 list-hosted-zones --output json)
ZONE_ID=$(echo $ZONES | jq -r ".HostedZones[] | select(.Name==\"$DOMAIN.\") | .Id")

if [ -z $ZONE_ID ]; then
  echo "Domain $DOMAIN not found in Route53"
  exit 5
fi

echo "Deleting DNS records in Route53"
FIP1=$(dig +short api.$CLUSTER_NAME.$DOMAIN)
FIP2=$(dig +short x.apps.$CLUSTER_NAME.$DOMAIN)

RESPONSE=$(aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch '{ "Comment": "Delete A record for cluster API", "Changes": [ { "Action": "DELETE", "ResourceRecordSet": { "Name": "api.'$CLUSTER_NAME'.'$DOMAIN'", "Type": "A", "TTL":  60, "ResourceRecords": [ { "Value": "'$FIP1'" } ] } } ] }' --output json)

if [ $? != 0 ]; then
  echo "Failed to delete A records for the cluster"
  exit 6
fi

echo "Waiting for DNS change to propagate"
aws route53 wait resource-record-sets-changed --id $(echo $RESPONSE | jq -r '.ChangeInfo.Id')

RESPONSE=$(aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch '{ "Comment": "Delete A record for cluster ingress", "Changes": [ { "Action": "DELETE", "ResourceRecordSet": { "Name": "*.apps.'$CLUSTER_NAME'.'$DOMAIN'", "Type": "A", "TTL":  60, "ResourceRecords": [ { "Value": "'$FIP2'" } ] } } ] }' --output json)

if [ $? != 0 ]; then
  echo "Failed to delete A records for the cluster, it's OK if previous installation failed."
else
  echo "Waiting for DNS change to propagate"
  aws route53 wait resource-record-sets-changed --id $(echo $RESPONSE | jq -r '.ChangeInfo.Id')
fi

echo "Releasing the floating IPs"
openstack floating ip delete $FIP1 $FIP2

echo "Removing directory \"cluster/$CLUSTER_NAME\""
rm -rf cluster/$CLUSTER_NAME

echo "List of all OpenStack resources with name containing \"$CLUSTER_NAME\""
sh $DIR/list-all-resources.sh $CLUSTER_NAME
