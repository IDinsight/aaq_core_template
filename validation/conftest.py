from pathlib import Path

import pytest
import sqlalchemy
import yaml
from core_model.app import create_app, get_config_data
from sqlalchemy import text


@pytest.fixture(scope="session")
def test_params():
    with open(Path(__file__).parent / "config.yaml", "r") as stream:
        params_dict = yaml.safe_load(stream)

    return params_dict


@pytest.fixture(scope="session")
def client(test_params, clean_start):
    app = create_app(test_params)
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="session")
def clean_start(db_engine):
    with db_engine.connect() as db_connection:
        t = text("DELETE FROM faqmatches WHERE faq_author='Validation author'")
        t2 = text("DELETE FROM inbounds")
        with db_connection.begin():
            db_connection.execute(t)
        with db_connection.begin():
            db_connection.execute(t2)


@pytest.fixture(scope="session")
def db_engine(test_params):
    config = get_config_data(test_params)
    uri = config["SQLALCHEMY_DATABASE_URI"]
    engine = sqlalchemy.create_engine(uri)
    yield engine
