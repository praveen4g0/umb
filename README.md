# umb

* To run locally use podman/docker to build image
```
docker build -t <> .

```
* umb brokers deployed behind the vpn to test this up use network `host` instead
```
docker run -it --network=host  quay.io/praveen4g0/umb-consumer:v0.0.1 /bin/bash

(app-root) python app.py  <-c optional config path >

```

* As of now we support 2 routes 
    1. `/consume` will help you to register with umb consumerService
    2. `/stop` will help you to stop registred services!