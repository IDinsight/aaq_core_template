import os
from pathlib import Path

import pytest
import yaml
from sqlalchemy import text

insert_faq = (
    "INSERT INTO faqmatches ("
    "faq_tags,faq_questions, faq_author, faq_title, faq_content_to_send, "
    "faq_added_utc, faq_thresholds) "
    "VALUES (:faq_tags, :faq_questions,:faq_author, :faq_title, :faq_content_to_send, "
    ":faq_added_utc, :faq_threshold)"
)

faq_other_params = {
    "faq_added_utc": "2022-04-14",
    "faq_author": "Pytest refresh",
    "faq_threshold": "{0.1, 0.1, 0.1, 0.1}",
    "faq_questions": """{"Dummmy question 1", "Dummmy question 2", "Dummmy question 3", "Dummmy question 4","Dummmy question 5","Dummy question 6"}""",
}


@pytest.fixture(scope="class")
def sample_faq_data():
    full_path = Path(__file__).parent / "data/faq_data.yaml"
    with open(full_path) as file:
        yaml_dict = yaml.full_load(file)
    return yaml_dict["faq_refresh_data"]


@pytest.fixture
def load_faq_data(client, db_engine, sample_faq_data):
    headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
    with db_engine.connect() as db_connection:
        inbound_sql = text(insert_faq)
        for i, sample_data in enumerate(sample_faq_data):
            db_connection.execute(
                inbound_sql,
                **sample_data,
                **faq_other_params,
            )
    yield
    with db_engine.connect() as db_connection:
        t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest refresh'")
        db_connection.execute(t)
    client.get("/internal/refresh-faqs", headers=headers)


class TestHealthCheck:
    def test_health_check_fails_with_no_faqs_status(self, client):
        response = client.get("/healthcheck")
        assert response.status_code == 500

    def test_health_check_fails_with_no_faqs_message(self, client):
        page = client.get("/healthcheck")
        assert page.data == b"No FAQs in database"

    def test_can_access_health_check(self, client, load_faq_data):
        response = client.get("/healthcheck")
        assert response.status_code == 200

    def test_health_check_successful(self, client, load_faq_data):
        page = client.get("/healthcheck")
        assert page.data == b"Healthy - all checks complete"


class TestRefresh:
    def test_refresh_of_six_faqs(self, load_faq_data, client):
        request_data = {
            "text_to_match": "I love going hiking. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()

        assert len(json_data["top_responses"]) == 0

        response = client.get("/internal/refresh-faqs", headers=headers)
        assert response.status_code == 200
        assert response.get_data() == b"Successfully refreshed 6 FAQs"
