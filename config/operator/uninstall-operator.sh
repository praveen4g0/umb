#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
source $DIR/commons.sh

echo ">> Uninstalling OpenShift Gitops operator"

deployments=$(oc get deployments -n openshift-gitops --no-headers -o name 2>/dev/null)

# Delete instance (name: cluster) of gitopsservices.pipelines.openshift.io
oc delete --ignore-not-found=true gitopsservices.pipelines.openshift.io cluster 2>/dev/null || fail_test "Unable to delete gitopsservice cluster instance"

wait_until_object_doesnt_exist "gitopsservices.pipelines.openshift.io" "cluster" "openshift-gitops" || fail_test "gitops service haven't deleted successfully"

# wait for pods deployments to be deleted in gitops namespace
for deployment in $deployments; do
   oc wait --for=delete $deployment -n openshift-gitops --timeout=5m || fail_test "Failed to delete deployment: $deployment in openshift-gitops namespace"
done

oc delete $(oc get csv  -n openshift-operators -o name|grep gitops) -n openshift-operators || fail_test "Unable to delete CSV"

oc delete -n openshift-operators installplan $(oc get subscription openshift-gitops-operator -n openshift-operators -o jsonpath='{.status.installplan.name}') || fail_test "Unable to delete installplan"

oc delete subscription openshift-gitops-operator -n openshift-operators --cascade=background || fail_test "Unable to delete subscription"

echo -e ">> Delete arogo resources accross all namespaces"
for res in applications applicationsets appprojects argocds; do
    oc delete --ignore-not-found=true ${res}.argoproj.io --all 
done

echo -e ">> Cleanup existing crds"
for res in applications applicationsets appprojects argocds; do
    oc delete --ignore-not-found=true crds ${res}.argoproj.io 
done

echo -e ">> Delete \"openshift-gitops\" project"
oc delete project openshift-gitops