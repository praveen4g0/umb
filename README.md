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
## Producer service
* You can find implementation code under `producer` section
* As of now we support route `produce`
    1. will help user to produce messages to required topic. (`POST`)

* Now you can deploy this services on any openshift cluster deployed behind the vpn! (psi)

### Pre-requistes
- setup configmaps & secrets prior
```
oc apply -f configs/configmap.yaml

oc apply -f configs/secrets.yaml

```

### Consumer service

```
oc apply -f consumer/openshift/imagestream.yaml

oc apply -f consumer/openshift/build-config.yaml

oc apply -f consumer/openshift/deployment-config.yaml

oc rollout status dc/umb-consumer

```

### Producer service

```
oc apply -f producer/openshift/imagestream.yaml

oc apply -f producer/openshift/build-config.yaml

oc apply -f producer/openshift/deployment-config.yaml

oc rollout status dc/umb-producer

oc apply -f producer/openshift/service.yaml

oc get route umb-service --template='http://{{.spec.host}}'

```

* Now user should be able to post message json or text message to any topic

```
 curl -X POST -H 'Content-Type: application/json' <umb-service-route-url>/produce -d '{"topic": "topic://VirtualTopic.qe.ci.product-scenario.test.complete", "message": {}}'               

Response: 

{
    "Message": "message sent successfully! to topic topic://VirtualTopic.qe.ci.product-scenario.test.complete"
}

```

## UMB notifications
You can easily produce a message to UMB topic to notify if your pipeline has failed or run sucessfully. There is a script in `misc/send-umb-interop-notifier.py` or `misc/send-umb-iib-notifier.py` that can help you with that, with the help of the finally tasks in your pipeline.

At the end of your pipeline add this block :
```
  finally:
  - name: finally
    workspaces:
    - name: kubeconfig
      workspace: kubeconfig
    taskSpec:
      workspaces:
      - name: kubeconfig
      steps:
        - name: send-umb-notification
          env:
            - name: UMB_WEBHOOK_URL
              value: "http://umb-service-umb.apps.cicd.tekton.codereadyqe.com/produce"
            - name: PIPELINERUN
              valueFrom:
                fieldRef:
                  fieldPath: metadata.labels['tekton.dev/pipelineRun'] 
            - name: LOG_URL
              value: "openshift"
            - name: VERSION
              value: $(tt.params.layered_product_version)
            - name: XUNIT_URLS
              value:  $(tt.params.artifacts)
            - name: KUBECONFIG
              value: $(workspaces.kubeconfig.path)/kubeconfig  
          image: quay.io/praveen4g0/umb-notifier:latest
          command: ["/code/send-umb-interop-notifier.py"] 
          # command: ["/code/send-umb-iib-notifier.py"]
```