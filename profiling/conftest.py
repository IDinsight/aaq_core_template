from pathlib import Path

import pytest
import sqlalchemy
import yaml

from core_model.app import create_app, get_config_data


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
def client(test_params):
    app = create_app(test_params)
    with app.test_client() as client:
        yield client


# db_engine scope changed to session
@pytest.fixture(scope="class")
def db_engine(test_params):
    config = get_config_data(test_params)
    uri = config["SQLALCHEMY_DATABASE_URI"]
    engine = sqlalchemy.create_engine(uri)
    yield engine
