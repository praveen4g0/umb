#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"

echo "Configure secrets"

if [ ! -f "$DIR/secrets.env" ]; then
  echo "You have to provide file $DIR/secrets.env!"
  exit 1
fi

if [ ! -f "$DIR/pull-secret" ]; then
  echo "You have to provide file $DIR/pull-secret! You can download it from https://www.openshift.com/try."
  exit 2
fi

if [ ! -f "$DIR/psi-gitops-shared.pem" ]; then
  echo "You have to provide file $DIR/psi-gitops-shared.pem! Ask any QE team member to share it with you."
  exit 2
fi

if [ ! -f "$DIR/psi-gitops-shared.pub" ]; then
  echo "You have to provide file $DIR/psi-gitops-shared.pub! Ask any QE team member to share it with you."
  exit 2
fi

source "$DIR/secrets.env"

if [[ "$OSTYPE" == "darwin"* ]]; then
  ENCODE_BASE64="base64"
else
  ENCODE_BASE64="base64 -w 0"
fi

ENCODED_PULL_SECRET=$(cat $DIR/pull-secret | $ENCODE_BASE64)
ENCODED_SSH_PRIVATE_KEY=$(cat $DIR/psi-gitops-shared.pem | $ENCODE_BASE64)
SSH_PUBLIC_KEY=$(cat $DIR/psi-gitops-shared.pub)
QUAY_IO_USERNAME=$(cat $DIR/pull-secret | jq -r '.auths["quay.io"].auth' | base64 -d | cut -d":" -f1)
QUAY_IO_PASSWORD=$(cat $DIR/pull-secret | jq -r '.auths["quay.io"].auth' | base64 -d | cut -d":" -f2)
REGISTRY_RH_IO_USERNAME=$(cat $DIR/pull-secret | jq -r '.auths["registry.redhat.io"].auth' | base64 -d | cut -d":" -f1)
REGISTRY_RH_IO_PASSWORD=$(cat $DIR/pull-secret | jq -r '.auths["registry.redhat.io"].auth' | base64 -d | cut -d":" -f2)

echo -e "\nConfiguring AWS credentials"
sed -e "s,\$AWS_ACCESS_KEY_ID,$AWS_ACCESS_KEY_ID,g" \
    -e "s,\$AWS_SECRET_ACCESS_KEY,$AWS_SECRET_ACCESS_KEY,g" \
    "$DIR/../../ci/secrets/aws.yaml" | oc apply -f -


echo -e "\nConfiguring Flexy secrets"
sed -e "s,\$AWS_ACCESS_KEY_ID,$AWS_ACCESS_KEY_ID,g" \
    -e "s,\$AWS_SECRET_ACCESS_KEY,$AWS_SECRET_ACCESS_KEY,g" \
    -e "s,\$AWS_OSD_ACCESS_KEY_ID,$AWS_OSD_ACCESS_KEY_ID,g" \
    -e "s,\$AWS_OSD_SECRET_ACCESS_KEY,$AWS_OSD_SECRET_ACCESS_KEY,g" \
    -e "s,\$DYNDNS_USERNAME,$DYNDNS_USERNAME,g" \
    -e "s,\$DYNDNS_PASSWORD,$DYNDNS_PASSWORD,g" \
    -e "s,\$OCM_TOKEN_PROD,$OCM_TOKEN_PROD,g" \
    -e "s,\$OCM_TOKEN_STAGE,$OCM_TOKEN_STAGE,g" \
    -e "s,\$PSI_CLOUD_USERNAME,$PSI_CLOUD_USERNAME,g" \
    -e "s,\$PSI_CLOUD_PASSWORD,$PSI_CLOUD_PASSWORD,g" \
    -e "s,\$PULL_SECRET,$ENCODED_PULL_SECRET,g" \
    -e "s,\$QUAY_IO_USERNAME,$QUAY_IO_USERNAME,g" \
    -e "s,\$QUAY_IO_PASSWORD,$QUAY_IO_PASSWORD,g" \
    -e "s,\$REGISTRY_RH_IO_USERNAME,$REGISTRY_RH_IO_USERNAME,g" \
    -e "s,\$REGISTRY_RH_IO_PASSWORD,$REGISTRY_RH_IO_PASSWORD,g" \
    -e "s,\$SSH_PRIVATE_KEY,$ENCODED_SSH_PRIVATE_KEY,g" \
    -e "s,\$SSH_PUBLIC_KEY,$SSH_PUBLIC_KEY,g" \
    "$DIR/../../ci/secrets/flexy.yaml" | oc apply -f -

echo -e "\nConfiguring image registry secrets"
sed -e "s,\$BREW_USER,$BREW_USER,g" \
    -e "s,\$BREW_PASS,$BREW_PASS,g" \
    -e "s,\$QUAY_USER,$QUAY_USER,g" \
    -e "s,\$QUAY_PASS,$QUAY_PASS,g" \
    "$DIR/../../ci/secrets/registry.yaml" | oc apply -f -

echo -e "\nConfiguring Uploader secrets"
sed -e "s/\$UPLOADER_USERNAME/$UPLOADER_USERNAME/" \
    -e "s/\$UPLOADER_PASSWORD/$UPLOADER_PASSWORD/" \
    -e "s|\$UPLOADER_HOST|$UPLOADER_HOST|" \
    "$DIR/../../ci/secrets/uploader.yaml" | oc apply -f -  