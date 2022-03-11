Uploader service
===========================

Artifacts generated during pipeline execution that we want to store for longer time (test suite results, 
installed cluster metadata, logs) are being uploaded to the so-called uploader service.

* Production (used by pipelines in the namespace `devtools-gitops-services`): http://uploader-devtools-gitops-services.apps.ocp-c1.prod.psi.redhat.com

Deployment
----------

1. `git clone https://github.com/chmouel/go-simple-uploader.git`
2. `cd go-simple-uploader/openshift`
3. `htpasswd -b -c configs/osinstall.htpasswd someusername somepassword` (use the one in config/secrets/secrets.env)
4. `oc project devtools-gitops-services`
5. `make deploy`
6. Create a route and update/create CNAME record in Route53.

```
kind: Route
apiVersion: route.openshift.io/v1
metadata:
  name: uploader2
  namespace: stage
  labels:
    app: uploader
spec:
  host: artifacts-stage.ospqa.com
  to:
    kind: Service
    name: uploader
    weight: 100
  port:
    targetPort: 8080-tcp
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
```