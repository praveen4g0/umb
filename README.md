OpenShift Gitops Plumbing
============================

This repo holds configuration for infrastructure and pipelines used for testing releases of OpenShift Gitops

At the moment it only contains scripts for manual provisioning and deprovisioning of OpenShift clusters on PnT Shared Infrastructure (PSI).

Prerequisites
-------------

1. Pull secrets for installation of OpenShift clusters. To obtain yours, go to https://www.openshift.com/try -> “Try it in the cloud” -> AWS, click on “Installer-Provisioned Infrastructure”, and click on “Download Pull Secret”. Save it somewhere, e.g. ~/some-dir/pull-secret.json
2. AWS account - although the scripts use PSI to deploy clusters, we use Amazon Route53 for DNS. Ask QE for account.
3. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) - name your AWS credentials profile `aws-gitops`
4. PSI account - access is managed by Rover group [psi-gitops-users](https://rover.redhat.com/groups/group/gitops). Ask group owner for access.
5. [OpenStack CLI](https://pypi.org/project/python-openstackclient/) - this repo already contains `clouds.yaml` file, you need to change username in it and create `~/.config/openstack/clouds.yaml` containing your Kerberos password.
6. OpenShift Installer binary on your `PATH`. You can download whatever version you need, scripts should work with all versions since 4.2. Browse the directories in [mirror.openshift.com](https://mirror.openshift.com/pub/openshift-v4/clients/), e.g. [stable 4.4](https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable-4.4/) or [nightly 4.5](https://mirror.openshift.com/pub/openshift-v4/clients/ocp-dev-preview/latest-4.5/). 
7. Needs `yq` and `jq` should be installed too.

### Example secure.yaml
 ```yaml
clouds:
  psi-gitops:
    auth:
      password: 'yourKerberosPassword'
```

Installing a New OpenShift Cluster
-------------------------------

Script `install-ipi-cluster.sh` is pre-configured to install default IPI clusters on PSI. The configuration of OpenShift installer is stored in file [install-config-template.yaml](./install-config-template.yaml).

The script has two required parameters - path to your pull secrets file and cluster name. Cluster name will be part of all URLs of the cluster.

> NOTE If you try to re-use the name of the cluster, first make sure that the cluster doesn't exist anymore.
> HACK: To speed up provisioning of clusters 

> NOTE The installer is able to download RHCOS image but when you run the script from outside of PSI DC, it will probably take too long and installer will time out. There are lastest official images `rhcos-4.6` and `rhcos-4.7` already uploaded in PSI so you can use that one and speed up the process.

```
OPENSHIFT_INSTALL_OS_IMAGE_OVERRIDE=rhcos-4.9
PULL_SECRET_FILE=~/some-dir/pull-secret.json
./install-ipi-cluster.sh mycluster
```

The script does the following:

1. Allocates a floating IP that will be used for API
2. Creates a DNS record for API
3. Runs the OpenShift installer

When the installation succeeds, you need to run script [post-install.sh](./post-install.sh):

```
./post-install.sh  mycluster
```

This script performs following steps:

1. Allocates a floating IP that will be used for ingress (Console and all user's applications)
2. Creates a wildcard DNS record for ingress
3. Configures authentication in cluster

When both scripts succeed, your cluster will be available on these URLs
* https://console-openshift-console.apps.mycluster.ocp-gitops-qe.com/
* https://api.mycluster.ocp-gitops-qe.com:6443

You can find `kubeadmin` and testing users' passwords in the logs. Additionally, `kubeadmin` password will be also stored in [./cluster/mycluster/auth/kubeadmin-password](./cluster/mycluster/auth/kubeadmin-password).

Destroying an OpenShift Cluster
-------------------------------

To remove an unneeded or misbehaving cluster or to cleanup after failed installation, run

```
./destroy-cluster.sh mycluster
```

> NOTE This will work only if the directory `cluster/mycluster` exists!

This script will perform following steps:

1. Runs the OpenShift installer which tries to remove all OpenStack resources associated with given cluster
2. Removes DNS records for the cluster
3. Removes the directory `cluster/mycluster`
4. Runs the script `list-all-resources.sh` that you can quickly verify that everthing was removed correctly.

Notes
-----

Our PSI account is already configured but [this document](https://docs.google.com/document/d/1aoJHLbdMy9TNlMyk-zea94eS2N0PN7YRe1deYpZNYzg) explains what needs to be done for new accounts. 

These scripts can only install OpenShift on PSI in IPI mode. With slight changes it would be possible to run it also on AWS in IPI mode. It's very probable that we will use containerized Flexy instead of these scripts in the near future. It's a tool used by multiple QE teams in Red Hat (including OpenShift QE) that can provision OpenShift clusters in various configurations (IPI, UPI, airgap) on multiple clouds.
==========