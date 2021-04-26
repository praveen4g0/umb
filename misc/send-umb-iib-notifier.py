#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Script to send a umb message to be plugged in a finally task"""
import argparse
import json
import os
import subprocess
import sys
import typing
import urllib.request
import datetime
import uuid


class UMBNotificationError(Exception):
    """Custom exception when we fail"""


def get_openshift_console_url(namespace: str) -> str:
    """Get the openshift console url for a namespace"""
    cmd = (
        "oc get route -n openshift-console console -o jsonpath='{.spec.host}'",
    )
    ret = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    if ret.returncode != 0:
        raise UMBNotificationError(
            "Could not detect the location of openshift console url: {ret.stdout.decode()}"
        )
    return f"https://{ret.stdout.decode()}/k8s/ns/{namespace}/tekton.dev~v1beta1~PipelineRun/"

def get_json_of_pipelinerun(pipelinerun: str) -> typing.Dict[str, typing.Dict]:
    """Find which namespace where we are running currently by checking the
    pipelinerun namespace"""
    cmd = f"oc get pipelinerun {pipelinerun} -o json"
    ret = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    if ret.returncode != 0:
        raise UMBNotificationError(f"Could not run command: {cmd}")
    return json.loads(ret.stdout)


def check_status_of_pipelinerun(
        jeez: typing.Dict[str, typing.Dict]) -> typing.List[str]:
    """Check status of a pipelinerun using kubectl, we avoid the the Running
    ones since we run in finally, it will have a running ones"""
    task_runs = jeez['status']['taskRuns']
    failed = []

    pname = jeez['metadata']['name']
    for task in task_runs.keys():
        bname = task.replace(pname + "-", '')
        bname = bname.replace("-" + bname.split("-")[-1], '')
        if bool([
                x['message'] for x in task_runs[task]['status']['conditions']
                if x['status'] != 'Running' and x['status'] == 'False'
        ]):
            failed.append(bname)
    return failed

def send_iib_test_complete_msg(webhook_url: str, iib: str,ocp_version: str,uid: str,pipelinerun: str,log_url: str) -> str:
    """Send a index image test complete message"""
    msg = {
    "artifact": {
      "advisory_id": "N/A",
      "brew_build_tag": "Undefined Brew Tag Name",
      "brew_build_target": "Undefined Brew Target Name",
      "component": "cvp-teamredhatopenshiftcontainerplatform",
      "full_name": "Undefined Artifact Image Full Name",
      "id": "1584936",
      "image_tag": "Undefined Artifact Image Tag",
      "issuer": "contra/pipeline",
      "name": "Undefined Artifact Image Name",
      "namespace": "Undefined Artifact Image Namespace",
      "nvr": "openshift-pipelines-operator-bundle-container-"+iib,
      "registry_url": "Undefined Artifact Image Registry URL",
      "scratch": "false",
      "type": "cvp"
    },
    "contact": {
      "docs": "",
      "email": "psi-pipelines@redhat.com",
      "name": "openshift-pipelines",
      "team": "openshift-pipelines",
      "url": "https://master-jenkins-csb-cnfqe.cloud.paas.psi.redhat.com/"
    },
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    "pipeline": {
      "build": uid,
      "id": pipelinerun,
      "name": "cnf-dev-jenkins-tests-pipeline"
    },
    "run": {
      "log": log_url,
      "url": "cvp-redhat-operator-bundle-image-validation-test"+"/console",
    },
    "system": [
      {
        "architecture": "x86_64",
        "os": "registry.ci.openshift.org/ocp/release:"+ocp_version,
        "provider": "openshift"
      }
    ],
    "test": {
      "category": "integration,functional,validation",
      "namespace": "cnf-ci",
      "result": "passed",
      "type": "smoke-test"
    },
    "version": "0.2.1"
  }
    data={"topic": "topic://VirtualTopic.eng.ci.product-build.test.complete", "message": msg}
  
    req = urllib.request.Request(webhook_url,
                                 data=json.dumps(data).encode(),
                                 headers={"Content-type": "application/json"},
                                 method="POST")
    # TODO: Handle error?
    return urllib.request.urlopen(req).read().decode()
    
def main() -> int:
    """Main"""
    parser = argparse.ArgumentParser()

    parser.add_argument("--log-url",
                        default=os.environ.get("LOG_URL"),
                        help="Link to the log url")

    parser.add_argument("--pipelinerun",
                        default=os.environ.get("PIPELINERUN"),
                        help="The pipelinerun to check the status on")

    parser.add_argument("--ocp-version",
                        default=os.environ.get("OCP_VERSION"),
                        help="The OCP version")                         

    parser.add_argument("--umb-webhook-url",
                        default=os.environ.get("UMB_WEBHOOK_URL"),
                        help="UMB webhook URL")

    parser.add_argument("--iib",
                        default=os.environ.get("IIB"),
                        help="The index image number")                    

    args = parser.parse_args()
    if not args.pipelinerun:
        print(
            "error --pipelinerun need to be set via env env variable or other means."
        )
        return 1

    if not args.version:
        print(
            "error --version need to be set via env env variable or other means."
        )
        return 1

    if not args.umb_webhook_url:
        print(
            "error --umb-webhook-url need to be set via env variable or other means."
        )
        return 1

    jeez = get_json_of_pipelinerun(args.pipelinerun)
    failures = check_status_of_pipelinerun(jeez)

    if args.log_url and args.log_url == "openshift":
        # TODO: Add tekton dashboard if we can find this automatically
        args.log_url = get_openshift_console_url(jeez['metadata']['namespace']) + \
            args.pipelinerun + "/logs"

    if failures:
        error_msg = f"""• *Failed Tasks*: {", ".join(failures)}\n"""
        print(error_msg)
        #TO_DO Implement send failed message to right topic(If exist). 
    else:
        ret = send_iib_test_complete_msg(args.umb_webhook_url, args.iib,args.ocp_version,str(uuid.uuid4()),args.pipelinerun,args.log_url)
        if ret:
            print(ret)
    return 0


if __name__ == '__main__':
    sys.exit(main())