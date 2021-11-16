#!/bin/bash

CLUSTER_NAME=$1
export AWS_PROFILE=${AWS_PROFILE:-"aws-gitops"}
export DOMAIN=${DOMAIN:-"ocp-gitops-qe.com"}
export NETWORK=${NETWORK:-"provider_net_cci_9"}
export OS_CLOUD=${OS_CLOUD:-"psi-gitops"}

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

if [ -z $PULL_SECRET_FILE ]; then
  echo "Environment variable PULL_SECRET_FILE not defined"
  exit 3
fi

if [ -d cluster/$CLUSTER_NAME ]; then
  read -r -n 1 -p "Directory \"cluster/$CLUSTER_NAME\" already exists. Do you want to delete it? (Yy|Nn) " REPLY
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "cluster/$CLUSTER_NAME"
  else
    exit 4
  fi
fi

mkdir "cluster/$CLUSTER_NAME"
cp install-config-template.yaml "cluster/$CLUSTER_NAME/install-config.yaml"

sed -i "s/clusternamexxx/$CLUSTER_NAME/" "cluster/$CLUSTER_NAME/install-config.yaml"

echo "Allocating a floating IP for cluster's API"
FIP=$(openstack floating ip create --description "$CLUSTER_NAME-api" -f value -c floating_ip_address $NETWORK)
if [ $? != 0 ]; then
  echo "Failed to allocate a floating IP for API"
  exit 10
fi

sed -i "s/ipxxx/$FIP/" cluster/$CLUSTER_NAME/install-config.yaml

sed -i "s/domainxxx/$DOMAIN/" cluster/$CLUSTER_NAME/install-config.yaml

sed -i "s/networkxxx/$NETWORK/" cluster/$CLUSTER_NAME/install-config.yaml

sed -i "s/computereplicasxxx/2/" cluster/$CLUSTER_NAME/install-config.yaml

sed -i "s/pullsecretxxx/$(cat $PULL_SECRET_FILE)/" cluster/$CLUSTER_NAME/install-config.yaml

#openshift-install --dir=cluster/$CLUSTER_NAME --log-level debug create manifests
# change the URL to upgrade info because it was installed using ci build
#sed -i "s/api.openshift.com\/api\/upgrades_info\/v1\/graph/openshift-release.svc.ci.openshift.org\/graph/" $CLUSTER_NAME/manifests/cvo-overrides.yaml

echo "Getting zone ID in Route53"
ZONES=$(aws route53 list-hosted-zones --output json)
ZONE_ID=$(echo $ZONES | jq -r ".HostedZones[] | select(.Name==\"$DOMAIN.\") | .Id")
if [ -z $ZONE_ID ]; then
  echo "Domain $DOMAIN not found in Route53"
  exit 20
fi

echo "Updating DNS records in Route53"
RESPONSE=$(aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch '{ "Comment": "Update A record for cluster API", "Changes": [ { "Action": "CREATE", "ResourceRecordSet": { "Name": "api.'$CLUSTER_NAME'.'$DOMAIN'", "Type": "A", "TTL":  60, "ResourceRecords": [ { "Value": "'$FIP'" } ] } } ] }' --output json)
if [ $? != 0 ]; then
  echo "Failed to update A record for cluster"
  echo "Releasing previously allocated floating IP"
  openstack floating ip delete $FIP
  exit 25
fi

echo "Waiting for DNS change to propagate"
aws route53 wait resource-record-sets-changed --id $(echo $RESPONSE | jq -r '.ChangeInfo.Id')

openshift-install --dir=cluster/$CLUSTER_NAME --log-level debug create cluster