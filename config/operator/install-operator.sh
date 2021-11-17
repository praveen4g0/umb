#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
source $DIR/commons.sh

CATALOG_SOURCE=${CATALOG_SOURCE:-"redhat-operators"}
CHANNEL=${CHANNEL:-"stable"}

function install_operator_sources() {
    echo -e ">>Ensure Gitops subscription exists"
    oc get subscription openshift-gitops-operator -n openshift-operators 2>/dev/null || \
    cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-gitops-operator
  namespace: openshift-operators
spec:
  channel: $CHANNEL
  installPlanApproval: Automatic
  name: openshift-gitops-operator
  source: $CATALOG_SOURCE
  sourceNamespace: openshift-marketplace
EOF
    
    wait_until_pods_running "openshift-operators" || fail_test "openshift gitops Operator controller did not come up"

    echo ">> Wait for GitopsService creation"
    wait_until_object_exist "gitopsservices.pipelines.openshift.io" "cluster" "openshift-gitops" || fail_test "gitops service haven't created yet"

    wait_until_pods_running "openshift-gitops" || fail_test "argocd controller did not come up"

    
    #Make sure that everything is cleaned up in the current namespace.
    for res in applications applicationsets appprojects appprojects; do
        oc delete --ignore-not-found=true ${res}.argoproj.io --all
    done
}

header "Installing gitops operator"
install_operator_sources