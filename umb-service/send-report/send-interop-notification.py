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
        "oc whoami --show-console",
    )
    ret = subprocess.run(cmd, shell=True, check=True, capture_output=True)
    if ret.returncode != 0:
        raise UMBNotificationError(
            "Could not detect the location of openshift console url: {ret.stdout.decode()}"
        )
    return f"{ret.stdout.decode()}/k8s/ns/{namespace}/tekton.dev~v1beta1~PipelineRun/"

def get_json_of_pipelinerun(pipelinerun: str, namespace: str) -> typing.Dict[str, typing.Dict]:
    """Find which namespace where we are running currently by checking the
    pipelinerun namespace"""
    cmd = f"oc get pipelinerun {pipelinerun} -n {namespace} -o json"
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

def send_interop_test_complete_msg(webhook_url: str, msg_id: str, layered_version: str, openshit_version: str, external_build_index_url: str, external_build_index_id: str, log_url: str, xunit_urls: str, test_complete_topic: str) -> str:
    """Send a interop test complete message"""
    msg = {
      "artifact": {
        "id": msg_id,
        "products": [
          {
            "architecture": "x86_64",
            "artifacts": [],
            "build": "GA",
            "id": "",
            "name": "openshift-gitops",
            "nvr": "openshift-gitops-"+layered_version,
            "phase": "testing",
            "release": "",
            "state": "interop ready",
            "type": "product-build",
            "version": layered_version
          },
          {
            "architecture": "x86_64",
            "artifacts": [],
            "build": "nightly",
            "external_build_index_url": external_build_index_url,
            "id": external_build_index_id,
            "internal_build_index_url": "n/a",
            "name": "openshift",
            "nvr": "openshift-"+openshit_version,
            "phase": "testing",
            "release": "",
            "state": "interop ready",
            "type": "product-build",
            "version": openshit_version
          }
        ],
        "type": "product-scenario"
      },
      "contact": {
        "docs": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team",
        "email": "pit-qe@redhat.com",
        "name": "PIQE Interop",
        "team": "PIQE Interop",
        "url": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team"
      },
      "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
      "run": {
        "log": log_url,
        "url": log_url+"/console"
      },
      "system": [
        {
          "architecture": "",
          "os": "",
          "provider": ""
        }
      ],
      "test": {
        "category": "interoperability",
        "namespace": "interop",
        "runtime": 2218,
        "type": "product-scenario",
        "xunit_urls": list(xunit_urls.split(","))
      },
      "version": "0.2.2"
    }
    data = {"topic": "topic://{test_complete_topic}", "message": msg}

    req = urllib.request.Request(webhook_url,
                                 data=json.dumps(data).encode(),
                                 headers={"Content-type": "application/json"},
                                 method="POST")
    # TODO: Handle error?
    return urllib.request.urlopen(req).read().decode()

def send_interop_test_error_msg(webhook_url: str, msg_id: str, layered_version: str, openshit_version: str, external_build_index_url: str, external_build_index_id: str, log_url: str, error_msg: str, test_error_topic: str) -> str:
    """Send a interop test error message"""
    msg = {
      "artifact": {
        "id": msg_id,
        "products": [
          {
            "architecture": "x86_64",
            "artifacts": [],
            "build": "GA",
            "id": "",
            "name": "openshift-gitops",
            "nvr": "openshift-gitops-"+layered_version,
            "phase": "testing",
            "release": "",
            "state": "interop ready",
            "type": "product-build",
            "version": layered_version
          },
          {
            "architecture": "x86_64",
            "artifacts": [],
            "build": "nightly",
            "build_index_url": external_build_index_url,
            "id": external_build_index_id,
            "name": "openshift",
            "nvr": "openshift-"+openshit_version,
            "phase": "testing",
            "release": "",
            "state": "interop ready",
            "type": "product-build",
            "version": openshit_version
          }
        ],
        "type": "product-scenario"
      },
      "contact": {
        "docs": "https://docs.engineering.redhat.com/display/PIT/Interoperability+Testing+Team",
        "email": "pit-qe@redhat.com",
        "name": "PIQE Interop",
        "team": "PIQE Interop",
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

    data = {"topic": "topic://{test_error_topic}", "message": msg}

    req = urllib.request.Request(webhook_url,
                                 data=json.dumps(data).encode(),
                                 headers={"Content-type": "application/json"},
                                 method="POST")
    # TODO: Handle error?
    return urllib.request.urlopen(req).read().decode()

def main() -> int:
    """Main"""
    parser = argparse.ArgumentParser()

    parser.add_argument("--msg-id",
                        default=os.environ.get("MSG_ID"),
                        help="Provide msg id")

    parser.add_argument("--log-url",
                        default=os.environ.get("LOG_URL"),
                        help="Link to the log url")

    parser.add_argument("--pipelinerun",
                        default=os.environ.get("PIPELINERUN"),
                        help="The pipelinerun to check the status on")

    parser.add_argument("--namespace",
                        default=os.environ.get("NAMESPACE"),
                        help="Namespace on which resources exists")

    parser.add_argument("--layered-version",
                        default=os.environ.get("LAYERED_VERSION"),
                        help="The Layered product version")

    parser.add_argument("--openshift-version",
                        default=os.environ.get("OPENSHIFT_VERSION"),
                        help="The Opesnhift product version")

    parser.add_argument("--openshift-build-url",
                        default=os.environ.get("OPENSHIFT_BUILD_URL"),
                        help="The Opesnhift external build url")

    parser.add_argument("--openshift-build-id",
                        default=os.environ.get("OPENSHIFT_BUILD_ID"),
                        help="The Opesnhift external build id")


    parser.add_argument("--xunit-urls",
                        default=os.environ.get("XUNIT_URLS"),
                        help="The test artifacts url")

    parser.add_argument("--umb-webhook-url",
                        default=os.environ.get("UMB_WEBHOOK_URL"),
                        help="UMB webhook URL")

    parser.add_argument("--test-complete-topic",
                        default=os.environ.get("TEST_COMPLETE_TOPIC"),
                        help="Test complete topic")

    parser.add_argument("--test-error-topic",
                        default=os.environ.get("TEST_ERROR_TOPIC"),
                        help="Test error topic")

    args = parser.parse_args()
    if not args.pipelinerun:
        print(
            "error --pipelinerun need to be set via env env variable or other means."
        )
        return 1

    if not args.layered_version:
        print(
            "error --layered-version need to be set via env env variable or other means."
        )
        return 1

    if not args.umb_webhook_url:
        print(
            "error --umb-webhook-url need to be set via env variable or other means."
        )
        return 1

    jeez = get_json_of_pipelinerun(args.pipelinerun, args.namespace)
    failures = check_status_of_pipelinerun(jeez)

    if args.log_url and args.log_url == "openshift":
        # TODO: Add tekton dashboard if we can find this automatically
        args.log_url = get_openshift_console_url(jeez['metadata']['namespace']) + \
            args.pipelinerun + "/logs"

    if failures:
        error_msg = f"""• *Failed Tasks*: {", ".join(failures)}\n"""
        ret = send_interop_test_error_msg(args.umb_webhook_url, args.msg_id, args.layered_version, args.openshift_version, args.openshift_build_url, args.openshift_build_id, args.log_url, error_msg, args.test_error_topic)
        if ret:
            print(ret)
    elif args.xunit_urls:
        ret = send_interop_test_complete_msg(args.umb_webhook_url, args.msg_id, args.layered_version, args.openshift_version, args.openshift_build_url, args.openshift_build_id, args.log_url, args.xunit_urls, args.test_complete_topic)
        if ret:
            print(ret)
    return 0


if __name__ == '__main__':
    sys.exit(main())
