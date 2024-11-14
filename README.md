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
