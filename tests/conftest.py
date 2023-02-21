from pathlib import Path

import pytest
import sqlalchemy
import yaml
from sqlalchemy import text

from core_model import app
from core_model.app import create_app, get_config_data, load_embeddings


@pytest.fixture(
    params=[
        "google_w2v",
        pytest.param("simple_fasttext_with_faq", marks=pytest.mark.extended),
    ],
    scope="session",
)
def test_params(request):
    with open(Path(__file__).parent / "configs/base.yaml", "r") as stream:
        params_dict = yaml.safe_load(stream)

    with open(Path(__file__).parent / f"configs/{request.param}.yaml", "r") as stream:
        params_dict.update(yaml.safe_load(stream))

    return params_dict


@pytest.fixture(scope="session")
def embedding_bin(test_params):
    return load_embeddings(test_params["matching_model"])


@pytest.fixture(scope="session")
def monkeysession():
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def patchbinary(monkeysession, embedding_bin):
    monkeysession.setattr(app, "load_embeddings", lambda *x: embedding_bin)


@pytest.fixture(scope="session")
def app_main(test_params, patchbinary):
    app = create_app(test_params)
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
def app_weight(test_params, patchbinary):
    app = create_app(test_params)
    return app


@pytest.fixture(scope="session")
def client_weight(app_weight):
    app_weight.config["REDUCTION_FUNCTION"] = "mean_plus_weight"
    with app_weight.test_client() as client:
        yield client


@pytest.fixture(scope="session")
def app_context(test_params, patchbinary):
    test_params["CONTEXT_ACTIVE"] = True
    app = create_app(test_params)
    return app


@pytest.fixture(scope="session")
def client_context(app_context):
    with app_context.test_client() as client:
        yield client


@pytest.fixture(scope="class")
def db_engine(test_params):
    config = get_config_data(test_params)
    uri = config["SQLALCHEMY_DATABASE_URI"]
    engine = sqlalchemy.create_engine(uri)
    yield engine
