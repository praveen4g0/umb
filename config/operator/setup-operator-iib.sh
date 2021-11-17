#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
source $DIR/commons.sh

BREW_IIB_PREFIX="brew.registry.redhat.io/rh-osbs/iib"
MIRROR_REG=${MIRROR_REG:-"brew.registry.redhat.io"}

USERNAME=${USERNAME:-"|shared-qe-temp.zmns.153b77"}
PASSWORD=${PASSWORD:-""}
INDEX=${INDEX:-}
ENVIRONMENT=${ENVIRONMENT:-"pre-stage"}
CATALOG_SOURCE=${CATALOG_SOURCE:-"custom-operators"}

header "Setup p12n operator on $ENVIRONMENT environment"

test -z "${INDEX}" && {
              echo "INDEX env variable is required"
              exit 1
}

test -z "${PASSWORD}" && {
              echo "PASSWORD for mirror registry env variable is required"
              exit 1
}

ENVSTAGE="stage"

if [[ ${ENVIRONMENT} = ${ENVSTAGE} ]]; then
  BREW_IIB_PREFIX="brew.registry.redhat.io/rh-osbs/iib-pub-pending"
fi

INDEX_IMAGE=$BREW_IIB_PREFIX:$INDEX
echo -e "index image: $INDEX_IMAGE"

function reset() {
  rm -rf authfile
}

oc get secret pull-secret -n openshift-config -o jsonpath={.data."\.dockerconfigjson"} | base64 -d > authfile
trap reset ERR EXIT

echo "login into $MIRROR_REG registry"
oc registry login  --insecure=true --registry=$MIRROR_REG --auth-basic="${USERNAME}:${PASSWORD}" --to=authfile

echo "set brew-registry authtication details to default pull-secret"
oc set data secret/pull-secret -n openshift-config --from-file=.dockerconfigjson=authfile
sleep 3
 
echo -e "Apply imagecontent source policy"
oc apply -f - << EOD
apiVersion: operator.openshift.io/v1alpha1
kind: ImageContentSourcePolicy
metadata:
  name: brew-registry
spec:
  repositoryDigestMirrors:
  - mirrors:
    - $MIRROR_REG
    source: registry.redhat.io
  - mirrors:
    - $MIRROR_REG
    source: registry.stage.redhat.io
  - mirrors:
    - $MIRROR_REG
    source: registry-proxy.engineering.redhat.com
EOD

echo -e "waiting for nodes to get restarted.."
machines=$(oc get machineconfigpool -o=jsonpath='{.items[*].metadata.name}{" "}')

sleep 60
for machine in ${machines}; do
    echo -e "waiting for machineconfigpool on node $machine to be in state Updated=true && Updating=false"
    while true; do
      sleep 3
      oc wait --for=condition=Updated=True -n openshift-operators machineconfigpool $machine --timeout=5m && \
      oc wait --for=condition=Updating=False -n openshift-operators machineconfigpool $machine --timeout=5m > /dev/null 2>&1 && \
      break
    done
done

sleep 3
echo -e "delete default operator sources"
oc patch operatorhub.config.openshift.io/cluster -p='{"spec":{"disableAllDefaultSources":true}}' --type=merge

echo -e "apply catalog source"
oc apply -f - << EOD
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: ${CATALOG_NAME}
  namespace: openshift-marketplace
spec:
  displayName: ${CATALOG_NAME}
  image: ${INDEX_IMAGE}
  publisher: openshift-gitops
  sourceType: grpc
  updateStrategy:
    registryPoll:
      interval: 20m
EOD

sleep 15
echo "waiting for pods in namespace openshift-marketplace to be ready...."
pods=$(oc -n openshift-marketplace get pods | awk '{print $1}' | grep $CATALOG_SOURCE)
for pod in ${pods}; do
    echo "waiting for pod $pod in openshift-marketplace to be in ready state"
    oc wait --for=condition=Ready -n openshift-marketplace pod $pod --timeout=5m
done