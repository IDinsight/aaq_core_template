import os

import pytest
from sqlalchemy import text


class TestInboundMessage:

    insert_faq = (
        "INSERT INTO faqmatches ("
        "faq_tags, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags, :author, :title, :content, :added_utc, :threshold)"
    )
    faq_tags = [
        """{"rock", "guitar", "melody", "chord"}""",
        """{"cheese", "tomato", "bread", "mustard"}""",
        """{"rock", "lake", "mountain", "sky"}""",
        """{"trace", "vector", "length", "angle"}""",
        """{"draw", "sing", "exercise", "code"}""",
        """{"digest", "eat", "chew", "expel"}""",
    ]
    faq_other_params = {
        "added_utc": "2022-04-14",
        "author": "Pytest author",
        "content": "{}",
        "threshold": "{0.1, 0.1, 0.1, 0.1}",
    }

    @pytest.fixture
    def faq_data(self, client, db_engine):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq)
            for i, tags in enumerate(self.faq_tags):
                db_connection.execute(
                    inbound_sql,
                    title=f"Pytest title #{i}",
                    faq_tags=tags,
                    **self.faq_other_params,
                )
        client.get("/internal/refresh-faqs", headers=headers)
        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        client.get("/internal/refresh-faqs", headers=headers)

    def test_inbound_returns_6_faqs(self, client, faq_data):
        """Since we insert only up to 6 messages in this test and the top_n_matches 
        is set to 10 in app config, the response will only return 6 faq names. 
        
        TODO: parametrize the test based on top_n_matches"""
        request_data = {
            "text_to_match": "I love going hiking. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()

        assert len(json_data["top_responses"]) == 6

    def test_inbound_endpoint_works(self, client):
        request_data = {
            "text_to_match": """ I'm worried about the vaccines. Can I have some
        information? \U0001f600
        πλέων ἐπὶ οἴνοπα πόντον ἐπ᾽ ἀλλοθρόους ἀνθρώπους, ἐς Τεμέσην""",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()
        assert "inbound_id" in json_data
        assert "scoring" in json_data
        assert "top_responses" in json_data
        assert "feedback_secret_key" in json_data


@pytest.mark.slow
class TestInboundFeedback:
    insert_inbound = (
        "INSERT INTO inbounds ("
        "inbound_text, feedback_secret_key, inbound_metadata, "
        "inbound_utc, model_scoring, returned_content, returned_utc) "
        "VALUES ('i am 12. Can i get the vaccine?', :secret_key, :metadata, :utc, :score, :content, :r_utc)"
    )
    inbound_other_params = {
        "secret_key": "abc123",
        "metadata": "{}",
        "utc": "2021-05-19",
        "score": "{}",
        "content": "{}",
        "r_utc": "2021-05-19",
    }

    @pytest.fixture(scope="class")
    def inbounds(self, db_engine):
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_inbound)
            db_connection.execute(inbound_sql, **self.inbound_other_params)

        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM inbounds")
            db_connection.execute(t)

    @pytest.fixture(scope="class")
    def inbound_id(self, inbounds, db_engine):
        with db_engine.connect() as db_connection:
            get_inbound_id_sql = text("SELECT MAX(inbound_id) FROM inbounds")
            results = db_connection.execute(get_inbound_id_sql)
            inbound_id = next(results)["max"]

        yield inbound_id

    def test_inbound_feedback_nonexistent_id(self, client):
        request_data = {"inbound_id": 0, "feedback_secret_key": "abcde", "feedback": ""}
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_data, headers=headers)
        assert response.status_code == 404
        assert response.data == b"No Matches"

    def test_inbound_feedback_wrong_feedback_key(self, inbound_id, client):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "wrong_secret_key",
            "feedback": "",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_data, headers=headers)
        assert response.status_code == 403
        assert response.data == b"Incorrect Feedback Secret Key"

    def test_inbound_feedback_success(self, inbounds, inbound_id, client):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "abc123",
            "feedback": "test_feedback",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_data, headers=headers)
        assert response.status_code == 200
        assert response.data == b"Success"
