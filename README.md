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

* As of now we support 2 routes 
    1. `/consume` will help you to register with umb consumerService
    2. `/stop` will help you to stop registred services!

* Now you can deploy this service on any openshift cluster deployed behind the vpn! (psi)
```
oc apply -f openshift/secrets.yaml

oc apply -f openshift/configmap.yaml

oc apply -f openshift/imagestream.yaml

oc apply -f openshift/buildConfig.yaml

oc apply -f openshift/depolymentConfig.yaml

oc rollout status dc/umb-psi-pipelines-robot-config

oc apply -f openshift/service.yaml

oc get route umb-service --template='http://{{.spec.host}} '

```
