"""Remove only the dev MLflow workload; preserve services, credentials and stored data."""
import json
import os
import subprocess

NAMESPACE = 'synthema-dev'
DEPLOYMENT = 'model-experiment-registry-deployment'


def kube(*args):
    return subprocess.check_output(
        ['kubectl', '--request-timeout=210s', '-n', NAMESPACE, *args], text=True)


def owned_by(resource, kind, names):
    return any(owner.get('kind') == kind and owner.get('name') in names
               for owner in resource.get('metadata', {}).get('ownerReferences', []))


def main():
    if os.environ.get('NAMESPACE', NAMESPACE) != NAMESPACE or os.environ.get('DEPLOYMENT', DEPLOYMENT) != DEPLOYMENT:
        raise ValueError('This cleanup job is limited to the dev MLflow deployment')
    # Snapshot ownership before deletion so orphaned replicas can also be removed.
    # Labels alone are insufficient: another deployment may also have app=mlflow.
    replica_sets = json.loads(kube('get', 'replicasets', '-o', 'json'))['items']
    targets = {item['metadata']['name'] for item in replica_sets
               if owned_by(item, 'Deployment', {DEPLOYMENT})}
    pods = json.loads(kube('get', 'pods', '-o', 'json'))['items']
    target_pods = {item['metadata']['name'] for item in pods
                   if owned_by(item, 'ReplicaSet', targets) or owned_by(item, 'Deployment', {DEPLOYMENT})}
    print(f'Removing deployment/{DEPLOYMENT} in {NAMESPACE}', flush=True)
    print(f'Owned leftovers: {len(targets)} ReplicaSets, {len(target_pods)} pods', flush=True)
    print(kube('delete', 'deployment', DEPLOYMENT, '--ignore-not-found=true',
               '--cascade=foreground', '--wait=true', '--timeout=180s'), end='', flush=True)
    for resource, names in [('replicaset', targets), ('pod', target_pods)]:
        for name in sorted(names):
            print(kube('delete', resource, name, '--ignore-not-found=true',
                       '--wait=true', '--timeout=60s'), end='', flush=True)
    print('MLflow workload removed. Database, artifacts, Services, Ingress, Secrets and PVCs were preserved.', flush=True)


if __name__ == '__main__':
    main()
