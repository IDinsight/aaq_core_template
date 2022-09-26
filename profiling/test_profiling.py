import os
from pathlib import Path

import pytest
import yaml
from sqlalchemy import text


class TestDummyFaqToDb:

    insert_faq = (
        "INSERT INTO faqmatches ("
        "faq_tags, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags, :faq_author, :faq_title, :faq_content_to_send, "
        ":faq_added_utc, :faq_threshold)"
    )

    faq_other_params = {
        "faq_added_utc": "2022-09-23",
        "faq_author": "Profiler author",
        "faq_threshold": "{0.1, 0.1, 0.1, 0.1}",
    }

    # delete pre-existing FAQs
    def test_clean_faq_db(self, db_engine):
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches")
            db_connection.execute(t)

            # check that db is now empty of faqs added by the profiler
            t = text("SELECT * FROM faqmatches")
            result = db_connection.execute(t)
            assert result.rowcount == 0

    # add dummy FAQs to db
    @pytest.fixture(scope="class")
    def sample_faq_data(self):
        full_path = Path(__file__).parent / "data/faq_data.yaml"
        with open(full_path) as file:
            yaml_dict = yaml.full_load(file)
        return yaml_dict["faq_refresh_data"]

    def test_load_faq_data(self, client, db_engine, sample_faq_data):
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq)
            for i, sample_data in enumerate(sample_faq_data):
                db_connection.execute(
                    inbound_sql,
                    **sample_data,
                    **self.faq_other_params,
                )
            # check that db now has content
            t = text("SELECT * FROM faqmatches")
            result = db_connection.execute(t)
            assert result.rowcount == 6

        # refresh FAQs
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        client.get("/internal/refresh-faqs", headers=headers)


class TestMainEndpoints:
    @pytest.fixture(scope="class")
    def inbound_chec_request(self, client):

        request_data = {
            "text_to_match": "Profiling test message.",
            "return_scoring": "false",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)

        return response

    def test_inbound_endpoint(self, inbound_chec_request):
        assert inbound_chec_request.status_code == 200

    def test_inbound_feedback(self, client, inbound_chec_request):

        inbound_id = inbound_chec_request.get_json()["inbound_id"]
        feedback_secret_key = inbound_chec_request.get_json()["feedback_secret_key"]

        feedback_json = {
            "inbound_id": inbound_id,
            "feedback_secret_key": feedback_secret_key,
            "feedback": {"feedback_type": "positive", "faq_id": 1},
        }

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=feedback_json, headers=headers)

        assert response.status_code == 200

    def test_accessing_valid_next_page(self, client, inbound_chec_request):
        next_page_url = inbound_chec_request.get_json()["next_page_url"]

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.get(next_page_url, headers=headers)

        assert response.status_code == 200


class TestCleanDb:
    def test_clean_faq_db(self, db_engine):
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches")
            db_connection.execute(t)

            # check that db is now empty of faqs added by the profiler
            t = text("SELECT * FROM faqmatches")
            result = db_connection.execute(t)
            assert result.rowcount == 0

    def test_clean_inbounds(self, db_engine):
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM inbounds")
            db_connection.execute(t)
