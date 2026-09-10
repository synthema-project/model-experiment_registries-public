"""Launch a one-off maintenance Job through Jenkins' Kubernetes credentials."""
import copy
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


def main():
    namespace = os.environ['NAMESPACE']
    deployment = os.environ['DEPLOYMENT']
    action = os.environ.get('DB_ACTION', 'upgrade')
    confirmation = os.environ.get('RESET_CONFIRMATION', '')
    if namespace != 'synthema-dev' or action not in ('upgrade', 'reset'):
        raise ValueError('Only synthema-dev upgrade/reset is supported')
    if os.environ.get('BACKUP_CONFIRMED', '').lower() != 'true':
        raise ValueError('Confirm a backup exists or the data is disposable')
    if action == 'reset' and confirmation != 'synthema-dev/mlflow':
        raise ValueError('Reset requires RESET_CONFIRMATION=synthema-dev/mlflow')

    def kubectl(*args, payload=None):
        return subprocess.check_output(
            ['kubectl', '--request-timeout=30s', '-n', namespace, *args],
            input=json.dumps(payload) if payload is not None else None,
            text=True, timeout=60,
        )

    deployed = json.loads(kubectl('get', 'deployment', deployment, '-o', 'json'))
    replicas = deployed['spec'].get('replicas', 1)
    selector = deployed['spec']['selector']
    if selector.get('matchExpressions'):
        raise ValueError('Unsupported deployment selector')
    template = copy.deepcopy(deployed['spec']['template'])
    # Do not match the server's Service or ReplicaSet selectors.
    name = 'mlflow-db-' + uuid.uuid4().hex[:12]
    template['metadata'] = {'labels': {'job-purpose': 'mlflow-db-maintenance'}}
    spec = template['spec']
    container = next(c for c in spec['containers'] if c['name'] == 'mlflow')
    spec['containers'] = [container]
    spec['restartPolicy'] = 'Never'
    for field in ('readinessProbe', 'livenessProbe', 'startupProbe', 'ports', 'lifecycle'):
        container.pop(field, None)
    container['command'] = ['python', '-c']
    container['args'] = [Path(__file__).with_name('db-maintenance.py').read_text()]
    injected = {'PYTHONPATH': '/mlflow-setup', 'DB_ACTION': action, 'RESET_CONFIRMATION': confirmation}
    container['env'] = [e for e in container.get('env', []) if e['name'] not in injected]
    container['env'].extend({'name': k, 'value': v} for k, v in injected.items())
    job = {'apiVersion': 'batch/v1', 'kind': 'Job', 'metadata': {'name': name},
           'spec': {'backoffLimit': 0, 'activeDeadlineSeconds': 900,
                    'ttlSecondsAfterFinished': 86400, 'template': template}}
    kubectl('create', '--dry-run=server', '-f', '-', payload=job)
    print(f'Scaling down {deployment}; maintenance Job: {name}', flush=True)
    kubectl('scale', 'deployment', deployment, '--replicas=0')
    # Wait until all matching pods, including terminating pods, have exited.
    labels = ','.join(f'{k}={v}' for k, v in selector['matchLabels'].items())
    deadline = time.monotonic() + 120
    while json.loads(kubectl('get', 'pods', '-l', labels, '-o', 'json'))['items']:
        if time.monotonic() > deadline:
            raise TimeoutError('MLflow pods did not stop; maintenance not started')
        time.sleep(3)
    kubectl('create', '-f', '-', payload=job)
    deadline = time.monotonic() + 960
    try:
        while True:
            status = json.loads(kubectl('get', 'job', name, '-o', 'json')).get('status', {})
            conditions = {c['type'] for c in status.get('conditions', []) if c['status'] == 'True'}
            if 'Complete' in conditions:
                break
            if 'Failed' in conditions or time.monotonic() > deadline:
                raise RuntimeError(f'Maintenance failed/timed out: {name}; deployment remains stopped')
            time.sleep(5)
    finally:
        try:
            print(kubectl('logs', 'job/' + name, '-c', 'mlflow', '--tail=100'))
        except subprocess.SubprocessError:
            print(f'Logs unavailable; inspect Job {name} in namespace {namespace}.')
    kubectl('scale', 'deployment', deployment, f'--replicas={replicas}')
    print(f'Maintenance succeeded; restored replicas to {replicas}.', flush=True)


if __name__ == '__main__':
    main()
