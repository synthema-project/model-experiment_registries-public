#!/usr/bin/env bash
# Functional checks against the deployed service; no test experiments are created.
set -euo pipefail

: "${NAMESPACE:=synthema}"
: "${SERVICE:=model-experiment-registry-service}"
check_dir=$(mktemp -d)
forward_pid=
cleanup() {
    if [[ -n "$forward_pid" ]]; then
        kill "$forward_pid" 2>/dev/null || true
        wait "$forward_pid" 2>/dev/null || true
    fi
    rm -rf "$check_dir"
}
trap cleanup EXIT

# Ask kubectl to allocate an unused local port, avoiding collisions on Jenkins.
kubectl -n "$NAMESPACE" port-forward --address 127.0.0.1 "service/$SERVICE" :80 >"$check_dir/forward.log" 2>&1 &
forward_pid=$!
port=
for ((attempt = 0; attempt < 30; attempt++)); do
    port=$(sed -n 's/.*127\.0\.0\.1:\([0-9][0-9]*\) ->.*/\1/p' "$check_dir/forward.log" | head -n 1)
    [[ -n "$port" ]] && break
    if ! kill -0 "$forward_pid" 2>/dev/null; then
        cat "$check_dir/forward.log" >&2
        exit 1
    fi
    sleep 1
done
if [[ -z "$port" ]]; then
    cat "$check_dir/forward.log" >&2
    echo 'Timed out waiting for the MLflow port-forward.' >&2
    exit 1
fi

base_url="http://127.0.0.1:$port"
curl_args=(--fail --silent --show-error --connect-timeout 5 --max-time 30)
curl "${curl_args[@]}" "$base_url/health" --output /dev/null
version=$(curl "${curl_args[@]}" "$base_url/version")
if [[ "$version" != '2.16.2' ]]; then
    echo "Expected MLflow 2.16.2, received: $version" >&2
    exit 1
fi
curl "${curl_args[@]}" -H 'Content-Type: application/json' \
    -d '{"max_results":1}' "$base_url/api/2.0/mlflow/experiments/search" --output /dev/null
curl "${curl_args[@]}" "$base_url/api/2.0/mlflow/registered-models/search?max_results=1" --output /dev/null
curl "${curl_args[@]}" "$base_url/api/2.0/mlflow/model-versions/search?max_results=1" --output /dev/null
echo "MLflow $version: health, experiment search, registered-model search, and model-version search passed."
