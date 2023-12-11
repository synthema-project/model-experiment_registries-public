FROM python:3.8-slim
ARG MLFLOW_VERSION=2.1.1

WORKDIR /mlflow/
RUN pip install --no-cache-dir mlflow==$MLFLOW_VERSION psycopg2-binary
