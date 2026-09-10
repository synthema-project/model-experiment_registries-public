"""Runs inside the maintenance pod, using the deployed MLflow version."""
import os

from sqlalchemy import MetaData, create_engine, inspect
from sqlalchemy.engine import make_url


def database_url():
    override = os.environ.get('BACKEND_STORE_URI')
    if override:
        url = make_url(override)
    else:
        # URL.create correctly handles reserved characters in credentials.
        url = make_url('postgresql://' + os.environ['POSTGRES_URL']).set(
            username=os.environ['POSTGRES_USER'],
            password=os.environ['POSTGRES_PASSWORD'],
            database=os.environ['POSTGRES_DB_NAME'],
        )
    if url.get_backend_name() != 'postgresql':
        raise ValueError('Maintenance requires PostgreSQL; pod-local SQLite cannot be maintained by a separate Job')
    return url


def main():
    action = os.environ['DB_ACTION']
    if action not in ('upgrade', 'reset'):
        raise ValueError('Unknown maintenance action')
    url = database_url()
    uri = url.render_as_string(hide_password=False)
    if action == 'reset':
        if url.database != 'mlflow' or os.environ.get('RESET_CONFIRMATION') != 'synthema-dev/mlflow':
            raise ValueError('Reset requires database mlflow and confirmation synthema-dev/mlflow')
        # Register both tracking and model registry tables in the shared metadata.
        from mlflow.store.tracking.dbmodels import models as tracking_models
        from mlflow.store.model_registry.dbmodels import models as registry_models
        from mlflow.store.db.base_sql_model import Base

        engine = create_engine(uri)
        try:
            with engine.begin() as connection:
                inspector = inspect(connection)
                if inspector.default_schema_name != 'public':
                    raise ValueError('Reset only supports the public schema')
                names = set(inspector.get_table_names(schema='public'))
                allowed = set(Base.metadata.tables) | {'alembic_version'}
                if names - allowed or inspector.get_view_names(schema='public'):
                    raise ValueError('Unexpected tables/views found; refusing to reset a potentially shared database')
                metadata = MetaData(schema='public')
                metadata.reflect(bind=connection, only=sorted(names))
                # No CASCADE: external dependencies must block deletion.
                metadata.drop_all(bind=connection)
        finally:
            engine.dispose()
        print('MLflow tables removed; initializing the schema.', flush=True)
    from mlflow.store.db.utils import _initialize_tables, _upgrade_db
    engine = create_engine(uri)
    try:
        if action == 'reset':
            _initialize_tables(engine)
        else:
            # Same migration function called by `mlflow db upgrade`.
            _upgrade_db(engine)
    finally:
        engine.dispose()
    print('Database maintenance completed.', flush=True)


if __name__ == '__main__':
    main()
