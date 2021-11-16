#!/bin/sh

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"

echo "Creating config map redhat-ca-config-map"
oc create configmap redhat-ca-config-map --from-file=ca.crt=$DIR/RH-IT-Root-CA.crt -n openshift-config

echo "Creating an LDAP identity provider"
oc apply -f $DIR/prod-oauth.yaml

echo "Creating group for admins"
oc apply -f $DIR/admin-group.yaml

echo "Syncing LDAP groups to the cluster"
oc adm groups sync --sync-config=$DIR/prod-ldap-sync.yaml --confirm

echo "Adding cluster-admin role to the group gitops-team-admins"
oc adm policy add-cluster-role-to-group cluster-admin gitops-team-admins

echo "Adding admin role to the group gitops-team in namespace \"gitops-ci\""
oc adm policy add-role-to-group admin gitops-team -n gitops-ci

echo "Deleting kubeadmin acccount"
oc delete secrets kubeadmin -n kube-system

