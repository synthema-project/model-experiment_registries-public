# MLFlow server

## Description
This project hosts the code for the Model and Experiment registry, where the AI models and tasks are managed and stored.

The component consists in a Mlflow Tracking Server working with a back-end postgres db and a Minio object storage bucket

### Structure
As Mlflow provides already an existing official docker image, there is no additional custom implementation and the project provides the resources to deploy the existing image and set it up.
The folder k8 provides the kubernetes resources while the folder templates and jenkins serve deployment purposes, with the corresponding Jenkinsfile and the enviornment setups in the templates folder

## Contributing
Pull requests are welcome. Please make sure to update tests as appropriate.

### Prerequisites
The usage of the code requires a set of tools to be present in your environment:

1. "mlflow" lib for python or "docker" (recommended) installed
1. A running instance of minio/ back-end object storage s3 of choice (if not standalone mode)
1. A running instance of postgres/ back-end database of choice (if not standalone mode)

### Setting up the environment
There are several configuration options to run the mlflow server depending on the desired backend. The mlflow server offers the option to work in a standalone mode hosting by itself the file storage and managing the database through an SQLAlchemy database (automatically deployed with the server)
1. Clone the repository

Standalone deployment:
1. Copy the .env from the templates folder with `cp templates/dotenv_standalone .env` and sync it with your deployment service (IDE or "--env-file .env" in docker run command).
Postgres and Minio as backend:
2. Copy the .env from the templates folder with `cp templates/dotenv_stack .env` and sync it with your deployment service (IDE or "--env-file .env" in docker run command). You will need to fill the ".env" file with the directions and credentials for the Postgres and MinIO apps.



### Bulding the images
Dockerhub mlflow image: ghcr.io/mlflow/mlflow:v2.16.2
To work with MinIO and Postgres backend, the container running the mlflow image will also require additional installations such as "boto3" and "psycopg2-binary" ("pip install psycopg2-binary boto3")


### Deploying app

#### Docker deployment
You can deploy the app in docker as follows.

1. To deploy the mlflow-server in docker (the standalone or stack version will be defined by the ".env" selected previously) run the command:  docker run -p 5000:5000 --env-file .env ghcr.io/mlflow/mlflow:v2.16.2 mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://<postgres-user>:<postgres-password>@<postgres-container-name>/<mlflow-db-name> --artifacts-destination s3://<buccket-name> --serve-artifacts
1. Go to [localhost:5000/](localhost:8000/docs) in the browser, to access mlflow Ui or use the provided interfaces to interact with it.

#### Kubernetes deployment
You can deploy the mlflow server in kubernetes adapt k8/deployment.yaml to the k8s cluster and run : "kubectl apply -f path/to/deployment.yaml"


## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
This project extend the usage of the MLFlow (mlflow) open software library for python which is registered under Apache 2.0 License, also compatible with the MIT License

### Kubernetes development without PostgreSQL

The deployment accepts `BACKEND_STORE_URI` from `mlflow-config`. Empty or unset
keeps the existing PostgreSQL backend. To use SQLite, set this in `k8/configmap.yml`:

```yaml
BACKEND_STORE_URI: "sqlite:////tmp/mlflow.db"
```

Apply the ConfigMap and deployment, then restart the pods to load the new value:

```sh
kubectl apply -f k8/configmap.yml -f k8/deployment.yaml
kubectl -n synthema-dev rollout restart deployment/model-experiment-registry-deployment
```

SQLite in `/tmp` is disposable: data is lost when the container is replaced.
Use one replica for this development setup. This does not migrate existing
PostgreSQL data. MinIO and its credentials are still required for artifacts;
the PostgreSQL secret keys must still exist but their values are not used.
Jenkins still requires its credential parameters. Restore an empty
`BACKEND_STORE_URI` and restart to reconnect to PostgreSQL.

### MLflow basic authentication

The Kubernetes server runs with `--app-name basic-auth` and installs
`mlflow[auth]==2.16.2`, matching the container version. The `mlflow-auth` Secret
supplies `/mlflow-auth/basic_auth.ini` via `MLFLOW_AUTH_CONFIG_PATH`.

For Jenkins deployments, supply `MLFLOW_TRACKING_USERNAME` and
`MLFLOW_TRACKING_PASSWORD` as the initial administrator credentials. The secret
helper creates the auth configuration without logging those values. Jenkins
requires Python 3 for configuration generation. Clients use the same environment
variables to authenticate; setting them on the server alone does not configure
its administrator account.

For a manual deployment, create a private `basic_auth.ini` file:

```ini
[mlflow]
default_permission = READ
database_uri = sqlite:////tmp/mlflow-auth.db
admin_username = <chosen-admin-username>
admin_password = <chosen-admin-password>
authorization_function = mlflow.server.auth:authenticate_request_basic_auth
```

Escape literal `%` characters as `%%` in this INI file. Create the Secret before
applying the deployment:

```sh
kubectl -n synthema-dev create secret generic mlflow-auth --from-file=basic_auth.ini
```

The authentication database is separate from `BACKEND_STORE_URI`. This dev
configuration stores users and permissions in disposable `/tmp/mlflow-auth.db`;
they reset on container replacement. Use one replica. For persistent deployments,
configure `database_uri` to a persistent SQL database or mounted SQLite volume.
Admin credentials in the INI initialize a new auth database; change existing
passwords through MLflow's user-management API.

The functional checks verify public health/version endpoints, a `401` for an
anonymous API request, and authenticated experiment/model searches. Run them with
the administrator client environment variables set. Docker deployments also need
the matching `mlflow[auth]` package, `--app-name basic-auth`, and a mounted auth INI
selected by `MLFLOW_AUTH_CONFIG_PATH` to enable authentication.


Jenkins manages `mlflow-secret` exclusively through `jenkins/mlflow-secret.sh`
using the build parameters. Do not apply `k8/mlflow-secret.yaml` afterward: it
would overwrite those credentials. The Secret name stays `mlflow-secret`; its
contents come from the form. PostgreSQL uses `POSTGRES_USER` / `POSTGRES_PASSWORD`,
MinIO uses `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, and MLflow basic auth uses
`MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD`.

The short storage service names in `k8/configmap.yml` resolve within the MLflow
pod's namespace (`synthema-dev`). For services in another namespace, use
`<service>.<namespace>.svc.cluster.local`. The explicit same-namespace MinIO URL
is `http://ostorage-svc-api.synthema-dev.svc.cluster.local:9000`; no wildcard is
used in Kubernetes service URLs.

### Database maintenance from Jenkins

Create a separate **Pipeline from SCM** job with Script Path
`jenkins/Jenkinsfile.clean-db`. It uses the existing Jenkins Kubernetes credential
(`k8s-admin` by default); SSH access to the cluster host is not needed. The Jenkins
agent needs Python 3 and kubectl. Its Kubernetes identity needs permission to read
Deployments/Pods, scale the Deployment, create/get Jobs, and read pod logs.

Run **Build with Parameters**:

- `DB_ACTION=upgrade` (default): run MLflow's database migrations while preserving
  tracking and registry records. Use this first for an older schema. It does not
  downgrade databases created by newer MLflow releases.
- `DB_ACTION=reset`: delete tracking and model registry tables, then initialize
  the schema for the deployed MLflow version. Type `synthema-dev/mlflow` in
  `RESET_CONFIRMATION`. This permanently removes experiments, runs, metrics,
  parameters, tags, and model registrations from PostgreSQL.
- Check `BACKUP_CONFIRMED` only after taking a backup, or if the development data
  is disposable. The pipeline does not create a backup automatically.

The pipeline reads the live Deployment, reuses its image, init containers and
Secret references, stops its pods, and runs a Job with retries disabled. It does
not apply the repository's static Secret. Do not run the normal deploy pipeline
or other MLflow instances against this database during maintenance.

Reset is restricted to PostgreSQL database `mlflow`, the `public` schema, and
recognized MLflow tables. Unexpected tables/views cause it to refuse deletion;
foreign dependencies are not removed with CASCADE. MinIO objects and MLflow's
separate authentication database are not cleaned by this operation. However,
stopping the server also discards the current pod-local authentication database,
so users/permissions reset to the configured initial administrator on restart.

After success, the original replica count is restored. After a failure or abort,
the Deployment remains stopped: inspect the maintenance Job logs in the Jenkins
output, resolve the cause, then retry maintenance as needed and run the normal
deployment pipeline to bring MLflow back. A retry starting at zero replicas will
restore zero replicas. Jobs have a 15-minute deadline and are retained for one day
for diagnostics. Pod-local SQLite cannot be migrated by this separate Job.
