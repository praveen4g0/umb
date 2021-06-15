export TOPIC=${TOPIC:-"VirtualTopic.qe.ci.product-scenario.pipelinesf2f.test.error"}
PN_TRACE_FRM=1 amq-consumer --env prod --certificate-file ./../consumer/config/psi-pipelines-robot.crt \
             --private-key  ./../consumer/config/psi-pipelines-robot.key \
             --ca-certs ./../consumer/config/RH-IT-Root-CA.crt \
             --address 'Consumer.psi-pipelines-robot.openshift-pipelines.'$TOPIC 