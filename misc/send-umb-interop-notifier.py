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

def send_interop_test_complete_msg(webhook_url: str, version: str,log_url: str, xunit_urls: str) -> str:
    """Send a interop test complete message"""
    msg = {
      "artifact": {
      "id": "4856",
      "products": [
        {
          "architecture": "x86_64",
          "artifacts": [],
          "build": "GA",
          "id": "",
          "name": "openshift-pipelines",
          "nvr": "openshift-pipelines-"+version,
          "phase": "testing",
          "release": "",
          "repos": [],
          "state": "interop ready",
          "subproduct": "Level2Guest",
          "type": "product-build",
          "version": version
        },
        {
          "architecture": "x86_64",
          "artifacts": [],
          "build": "RC1.0",
          "id": "RHEL-8.4.0-20210409.0",
          "image": "RHEL-8.4.0-20210409.0-x86_64",
          "name": "rhel",
          "nvr": "RHEL-8.4.0-20210409.0",
          "phase": "testing",
          "release": "",
          "repos": [
            {
              "base_url": "http://download.eng.bos.redhat.com/rhel-8/rel-eng/RHEL-8/RHEL-8.4.0-20210409.0/compose/BaseOS/x86_64/os",
              "name": "baseos"
            },
            {
              "base_url": "http://download.eng.bos.redhat.com/rhel-8/rel-eng/RHEL-8/RHEL-8.4.0-20210409.0/compose/AppStream/x86_64/os",
              "name": "appstream"
            }
          ],
          "state": "interop ready",
          "type": "product-build",
          "version": "8.4.0"
        }
      ],
      "type": "product-scenario"
    },
    "contact": {
      "docs": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team",
      "email": "psi-pipelines@redhat.com",
      "name": "Openshift Pipelines",
      "team": "Openshift Pipelines",
      "url": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team"
    },
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    "run": {
      "log": log_url,
      "url": log_url+"/console"
    },
    "system": [
      {
        "architecture": "x86_64",
        "os": "RHEL-8.4.0-20210409.0",
        "provider": "openstack",
        "variant": "BaseOS"
      }
    ],
    "test": {
      "category": "interoperability",
      "namespace": "interop",
      "type": "product-scenario",
      "xunit_urls": [xunit_urls]
    },
    "version": "0.2.2"
    }
    data={"topic": "topic://VirtualTopic.qe.ci.product-scenario.test.complete", "message": msg}
  
    req = urllib.request.Request(webhook_url,
                                 data=json.dumps(data).encode(),
                                 headers={"Content-type": "application/json"},
                                 method="POST")
    # TODO: Handle error?
    return urllib.request.urlopen(req).read().decode()

def send_interop_test_error_msg(webhook_url: str, version: str,log_url: str,error_msg: str) -> str:
    """Send a interop test complete message"""
    msg = {
      "artifact": {
      "id": "4875",
      "products": [
        {
          "architecture": "x86_64",
          "artifacts": [],
          "build": "GA",
          "id": "",
          "name": "openshift-pipelines",
          "nvr": "openshift-pipelines-"+version,
          "phase": "testing",
          "release": "",
          "repos": [],
          "state": "interop ready",
          "type": "product-build",
          "version": version
        },
        {
          "architecture": "x86_64",
          "artifacts": [],
          "build": "RC1.0",
          "id": "RHEL-8.4.0-20210409.0",
          "image": "RHEL-8.4.0-20210409.0-x86_64",
          "name": "rhel",
          "nvr": "RHEL-8.4.0-20210409.0",
          "phase": "testing",
          "release": "",
          "repos": [
            {
              "base_url": "http://download.eng.bos.redhat.com/rhel-8/rel-eng/RHEL-8/RHEL-8.4.0-20210409.0/compose/BaseOS/x86_64/os",
              "name": "baseos"
            },
            {
              "base_url": "http://download.eng.bos.redhat.com/rhel-8/rel-eng/RHEL-8/RHEL-8.4.0-20210409.0/compose/AppStream/x86_64/os",
              "name": "appstream"
            }
          ],
          "state": "interop ready",
          "type": "product-build",
          "version": "8.4.0"
        }
      ],
      "type": "product-scenario"
    },
    "contact": {
      "docs": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team",
      "email": "psi-pipelines@redhat.com",
      "name": "Openshift Pipelines",
      "team": "Openshift Pipelines",
      "url": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team"
    },
    "error": {
      "reason": error_msg
    },
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
    "run": {
      "log": log_url,
      "url": log_url+"/console"
    },
    "test": {
      "category": "interoperability",
      "namespace": "interop",
      "type": "product-scenario"
    },
    "version": "0.2.2"
    }

    data={"topic": "topic://VirtualTopic.qe.ci.product-scenario.test.error", "message": msg}
  
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

    parser.add_argument("--version",
                        default=os.environ.get("VERSION"),
                        help="The Layered product version")

    parser.add_argument("--xunit-urls",
                        default=os.environ.get("XUNIT_URLS"),
                        help="The test artifacts url")                                        

    parser.add_argument("--umb-webhook-url",
                        default=os.environ.get("UMB_WEBHOOK_URL"),
                        help="UMB webhook URL")

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
        ret = send_interop_test_error_msg(args.umb_webhook_url,args.version,args.log_url,error_msg)
        if ret:
            print(ret)
    elif args.xunit_urls:
        ret = send_interop_test_complete_msg(args.umb_webhook_url, args.version,args.log_url,args.xunit_urls)
        if ret:
            print(ret)

    return 0


if __name__ == '__main__':
    sys.exit(main())