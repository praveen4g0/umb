# OpenShift Gitops Plumbing

This repo holds configuration for infrastructure and gitops used for testing releases of OpenShift gitops.

## Downstream CI

gitops QE team maintain an OpenShift cluster in PSI with pipelines operator installed. We regularly update the cluster so that we use the latest release of OpenShift pipelines.

Access is managed by Rover group [gitops](https://rover.redhat.com/groups/group/gitops). Ask group owner for access, then use Kerberos credentials to log in.

Production pipelines run in namespace `gitops-ci`. Users are supposed to use their own namespaces when debugging, improving or developing pipelines.

## Installing an OpenShift cluster

We have a task and pipeline called `flexy-install` which can install OpenShift clusters in many configurations (version, PSI/AWS, regular/disconnected/proxy enabled).

Downstream CI is configured to provision clusters on PSI and AWS - use PSI whenever possible. Please remove your cluster as soon as you don't need it.


Display pipeline's description by running `tkn pipeline describe flexy-install -n gitops-ci`.

### Using pre-prepared YAML file

1. Login to Downstream CI cluster using your Kerberos credentials.
2. Clone this git repository.
3. Edit `ci/pipelineruns/flexy-install-psi.yaml`. In many cases only the name of the cluster will be required.

### Using tkn CLI

1. Login to Downstream CI cluster using your Kerberos credentials.
2. Clone this git repository.
3. Run `tkn pipeline start flexy-install -n gitops-ci -p CLUSTER_NAME=<choose_your_own_name> -w name=flexy-secrets,secret=flexy -w name=install-dir,claimName=install-dir -w name=plumbing-git,volumeClaimTemplateFile=ci/pvcs/template-100Mi.yaml --showlog`

### Using Devconsole

1. Login to Downstream CI cluster UI console.
2. Navigate to `Pipelines` section in `gitops-ci` namespace.
3. Open pipeline `flexy-install` and choose `Start` from `Actions` menu.
4. Follow input fields descriptions for what parameters to use. In many cases only the name of the cluster will be required.

> NOTE: Workspace descriptions are not displayed in OpenShift 4.7 and multi-line descriptions are hard to read in UI, open [flexy-install pipeline](./ci/pipelines/flexy-install.yaml) to read the docs.

## Uninstalling an OpenShift cluster

We have a task and pipeline called `flexy-uninstall` which can uninstall any cluster

Display pipeline's description by running `tkn pipeline describe flexy-uninstall -n gitops-ci`.
