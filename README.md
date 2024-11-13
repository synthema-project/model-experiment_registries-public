# Federated Learning Components

## Description
This project hosts the code for 


### Structure
The componentes are structured 
- The folder common provides 
- The folder apps includes 

## Contributing
Pull requests are welcome. Please make sure to update tests as appropriate.

### Prerequisites
Extending the code requires a set of tools to be present in your environment:

1. 
1. A running instance of rabbitmq -> see the [docker-compose.yml](docker-compose.yml) file.

### Setting up the environment

There are several configuration options that need to be established in order to start contributing.

The process is as follows:

1. Clone the repository
1. Copy the .env from the templates folder with `cp templates/dot_env .env` and sync it with your IDE. (In vscode this is done automatically if the file is named ".env"). Note that the path appended to both PYTHONPATH and MYPYPATH must be the root dir of this project.
1. Run the script [generate_envs.sh](scripts/generate_envs.sh) to create all dedicated venvs. **Note that the script generate_envs.sh install runs `poetry install` and creates a virtual environment by default in the home directory, if you want to set the project dir as the parent folder for the venv, then make sure to [config poetry](https://python-poetry.org/docs/configuration/#virtualenvsin-project).**


### Running tests and code checks
The main entrypoint for testing purposes is the file 

### Bulding the images
Dockerhub mlflow image: 



### Deploying app

#### Docker deployment
You can deploy the apps in docker as follows.

1. Open the [docker-compose.yml](docker-compose.yml) file and set the appropriate env variables for each component.
1. Run `docker compose up`to start the FL components and their dependencies.
1. Go to [localhost:8000/docs](localhost:8000/docs) in the browser, which is the [OpenAPI](https://www.openapis.org/) spec for the REST API.

#### Kubernetes deployment
You can deploy the apps in kubernetes 

### Running a federated learning job


## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
