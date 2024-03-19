FROM python:3.8-slim
ARG MLFLOW_VERSION=2.8.1

WORKDIR .
EXPOSE 5000
RUN pip install --no-cache-dir mlflow==$MLFLOW_VERSION psycopg2-binary SQLAlchemy
