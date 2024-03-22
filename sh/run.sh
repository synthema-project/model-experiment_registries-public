set -x

script_dir=$(dirname "$0")
cd "$script_dir/.."

# Load environment variables from .env file
export $(cat .env | xargs)

# Process the deployment.yaml with envsubst
envsubst < k8/deployment.yaml | kubectl apply -f -
