# umb

* To run locally use podman/docker to build image
```
docker build -t <image-name> .

```
* umb brokers deployed behind the vpn to test this up use network `host` instead
```
docker run -it --network=host <image-name> /bin/bash

(app-root) python app.py  <-c optional config path >

```

* As of now we support
    1. `/produce` will help user to produce text message! (`POST`)

* Now you can deploy this service on any openshift cluster deployed behind the vpn! (psi)
```
oc apply -f openshift/secrets.yaml

oc apply -f openshift/configmap.yaml

oc apply -f openshift/imagestream.yaml

oc apply -f openshift/buildConfig.yaml

oc apply -f openshift/depolymentConfig.yaml

oc rollout status dc/umb-psi-pipelines-robot-config

oc apply -f openshift/service.yaml

oc get route umb-service --template='http://{{.spec.host}}'

```

* Now user should be able to post message json or text message to any topic

```
 curl -X POST -H 'Content-Type: application/json' http://localhost:8080/produce -d '{"topic": "topic://VirtualTopic.qe.ci.product-scenario.test.complete", "message": {}}'               

Response: 

{
    "Message": "message sent successfully! to topic topic://VirtualTopic.qe.ci.product-scenario.test.complete"
}

```