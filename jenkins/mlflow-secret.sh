#!/usr/bin/env bash
# Build the Kubernetes Secret from Jenkins build parameters, without logging values.
set +x
set -euo pipefail

case "${1:-}" in
    validate) apply_args=(--dry-run=server) ;;
    apply) apply_args=() ;;
    *) echo 'Usage: mlflow-secret.sh validate|apply' >&2; exit 2 ;;
esac

: "${NAMESPACE:?NAMESPACE is required}"
: "${POSTGRES_USER:?Enter POSTGRES_USER in Build with Parameters}"
: "${POSTGRES_PASSWORD:?Enter POSTGRES_PASSWORD in Build with Parameters}"
: "${AWS_ACCESS_KEY_ID:?Enter AWS_ACCESS_KEY_ID in Build with Parameters}"
: "${AWS_SECRET_ACCESS_KEY:?Enter AWS_SECRET_ACCESS_KEY in Build with Parameters}"

umask 077
secret_dir=$(mktemp -d)
trap 'rm -rf "$secret_dir"' EXIT
# Files preserve special characters and keep credentials out of kubectl arguments.
printf '%s' "$POSTGRES_USER" > "$secret_dir/POSTGRES_USER"
printf '%s' "$POSTGRES_PASSWORD" > "$secret_dir/POSTGRES_PASSWORD"
printf '%s' "$AWS_ACCESS_KEY_ID" > "$secret_dir/AWS_ACCESS_KEY_ID"
printf '%s' "$AWS_SECRET_ACCESS_KEY" > "$secret_dir/AWS_SECRET_ACCESS_KEY"

kubectl -n "$NAMESPACE" create secret generic mlflow-secret \
    --from-file="POSTGRES_USER=$secret_dir/POSTGRES_USER" \
    --from-file="POSTGRES_PASSWORD=$secret_dir/POSTGRES_PASSWORD" \
    --from-file="AWS_ACCESS_KEY_ID=$secret_dir/AWS_ACCESS_KEY_ID" \
    --from-file="AWS_SECRET_ACCESS_KEY=$secret_dir/AWS_SECRET_ACCESS_KEY" \
    --dry-run=client -o json > "$secret_dir/secret.json"
kubectl -n "$NAMESPACE" apply "${apply_args[@]}" -f "$secret_dir/secret.json"
