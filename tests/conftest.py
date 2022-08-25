from pathlib import Path

import pytest
import sqlalchemy
import yaml
from sqlalchemy import text
from core_model.app import create_app, get_config_data, load_embeddings

# parameterize this to load different embeddings
# @pytest.fixture(scope="session")
# def embedding_bin():
#     return load_embeddings()


@pytest.fixture(scope="session")
def monkeysession(request):
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def test_params():
    with open(Path(__file__).parent / "config.yaml", "r") as stream:
        params_dict = yaml.safe_load(stream)

    return params_dict


@pytest.fixture(scope="session")
def app_main(test_params):
    app = create_app(test_params)
    app.faqt_model.n_top_matches = 3
    return app


@pytest.fixture(scope="class", autouse=True)
def clean_start(db_engine):
    with db_engine.connect() as db_connection:
        t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
        db_connection.execute(t)


@pytest.fixture(scope="session")
def client(app_main):
    with app_main.test_client() as client:
        yield client


@pytest.fixture(scope="session")
def app_weight(test_params):
    app = create_app(test_params)
    return app


@pytest.fixture(scope="session")
def client_weight(app_weight):
    app_weight.config["REDUCTION_FUNCTION"] = "mean_plus_weight"
    with app_weight.test_client() as client:
        yield client


@pytest.fixture(scope="session")
def test_params_other_model():
    with open(Path(__file__).parent / "config_test_other_model.yaml", "r") as stream:
        params_dict = yaml.safe_load(stream)

    return params_dict


@pytest.fixture(scope="session")
def app_other_model(test_params_other_model):
    app = create_app(test_params_other_model)
    return app


@pytest.fixture(scope="session")
def client_other_model(app_other_model):
    app_other_model.config["REDUCTION_FUNCTION"] = "mean_plus_weight"
    with app_other_model.test_client() as client:
        yield client


@pytest.fixture(scope="class")
def db_engine(test_params):
    config = get_config_data(test_params)
    uri = config["SQLALCHEMY_DATABASE_URI"]
    engine = sqlalchemy.create_engine(uri)
    yield engine
