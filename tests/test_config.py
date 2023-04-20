import os
import re
import secrets
from datetime import datetime

import pytest
from sqlalchemy import text


class TestConfig:
    insert_query = (
        "INSERT INTO contextualization("
        "version_id,config_added_utc,custom_wvs,"
        "pairwise_triplewise_entities, tag_guiding_typos, active)"
        "VALUES (:version_id, :date_added,:custom_wvs, :pairwise, :tags, :active);"
    )

    config_params = {
        "custom_wvs": """{"shots": {"vaccines": 1},"deliver": {"birth": 1}}""",
        "pairwise": """{"(flu, vaccine)": "flu_vaccine","(medical, aid)": "medical_aid"}""",
        "tags": """["side","sneeze","teeth","test", "vaccine"]""",
    }

    @pytest.fixture(scope="function")
    def add_config(self, db_engine):
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_query)
            db_connection.execute(
                inbound_sql,
                date_added=datetime.now(),
                version_id="pytest_config",
                active=True,
                **self.config_params,
            )
        yield
        with db_engine.connect() as db_connection:
            db_connection.execute("DELETE FROM contextualization")

    def test_language_context_endpoint(self, client, add_config):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.get("/config/edit-language-context", headers=headers)
        assert response.get_data(as_text=True) == "pytest_config"

    def test_language_context_endpoint_updates_config(
        self, client, app_main, add_config
    ):
        custom_wvs = eval(self.config_params["custom_wvs"])
        tags = eval(self.config_params["tags"])

        assert custom_wvs != app_main.faqt_model.glossary
        assert tags != app_main.faqt_model.tags_guiding_typos

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        client.get("/config/edit-language-context", headers=headers)

        assert custom_wvs == app_main.faqt_model.glossary
        assert tags == app_main.faqt_model.tags_guiding_typos
