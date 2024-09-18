set -x

script_dir=$(dirname "$0")
cd "$script_dir/.."

# Load environment variables from .env file
export $(cat .env | xargs)

# Process the manifest.yaml with envsubst
envsubst < k8/manifest.yaml | kubectl apply -f -
