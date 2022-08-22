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
def app(test_params):
    app = create_app(test_params)
    app.faqt_model.n_top_matches = 3
    return app


@pytest.fixture(scope="class", autouse=True)
def clean_start(db_engine):
    with db_engine.connect() as db_connection:
        t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
        db_connection.execute(t)


@pytest.fixture(scope="session")
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="session")
def client_weight(app):
    app.config["REDUCTION_FUNCTION"] = "mean_plus_weight"
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="class")
def db_engine(test_params):
    config = get_config_data(test_params)
    uri = config["SQLALCHEMY_DATABASE_URI"]
    engine = sqlalchemy.create_engine(uri)
    yield engine
