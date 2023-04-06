import os
import re

import pytest
from sqlalchemy import text


@pytest.fixture
def default_config(db_engine):
    with db_engine.connect() as db_connection:
        t = text("SELECT * FROM contextualization WHERE active=true")
        rs = db_connection.execute(t)
        return rs.mappings().one()


class TestConfig:
    def test_language_context_endpoint(self, client):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.get("/config/edit-language-context", headers=headers)
        assert re.search(
            "Language context successfully edited",
            response.get_data(as_text=True),
        )

    def test_language_context_endpoint_updates_config(
        self, client, app_main, default_config
    ):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.get("/config/edit-language-context", headers=headers)

        assert default_config["custom_wvs"] == app_main.faqt_model.glossary

        assert (
            default_config["tag_guiding_typos"]
            == app_main.faqt_model.tags_guiding_typos
        )
