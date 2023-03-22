from pathlib import Path

import pytest
import sqlalchemy
import yaml
from sqlalchemy.pool import NullPool

from core_model.app import create_app, get_config_data, init_faqt_model
from core_model.app.main import inbound


@pytest.fixture(scope="session")
def monkeysession():
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def patch_inbound_db(monkeysession):
    monkeysession.setattr(inbound, "save_inbound_to_db", lambda *x, **y: 123)


@pytest.fixture(scope="session")
def test_params():
    with open(Path(__file__).parent / "config.yaml", "r") as stream:
        params_dict = yaml.safe_load(stream)

    return params_dict


@pytest.fixture(scope="session")
def app_main(test_params, patch_inbound_db):
    app = create_app(test_params)
    init_faqt_model(app)
    return app


@pytest.fixture(scope="session")
def client(app_main):
    with app_main.test_client() as client:
        yield client


@pytest.fixture(scope="class")
def db_engine(test_params):
    config = get_config_data(test_params)
    uri = config["SQLALCHEMY_DATABASE_URI"]
    engine = sqlalchemy.create_engine(uri, poolclass=NullPool)
    yield engine
