import os
import re

import pytest
from sqlalchemy import text

insert_faq = (
    "INSERT INTO faqmatches ("
    "faq_tags,faq_questions,faq_contexts, faq_author, faq_title, faq_content_to_send, "
    "faq_added_utc, faq_thresholds) "
    "VALUES (:faq_tags, :faq_questions,:faq_contexts, :author, :title, :content, :added_utc, :threshold)"
)
faq_tags = [
    """{"rock", "guitar", "melody", "chord"}""",
    """{"cheese", "tomato", "bread", "mustard"}""",
    """{"rock", "lake", "mountain", "sky"}""",
    """{"trace", "vector", "length", "angle"}""",
    """{"draw", "sing", "exercise", "code"}""",
    """{"digest", "eat", "chew", "expel"}""",
]
faq_contexts = [
    """{"code", "deploy", "maintain"}""",
    """{"design","code","maintain"}""",
    """{ "test","deploy"}""",
    """{"design", "test", "deploy","maintain"}""",
    """{"design", "code","test"}""",
    """{"test"}""",
]
faq_other_params = {
    "added_utc": "2022-04-14",
    "author": "Pytest author",
    "threshold": "{0.1, 0.1, 0.1, 0.1}",
    "faq_questions": """{"Dummmy question 1", "Dummmy question 2", "Dummmy question 3", "Dummmy question 4","Dummmy question 5","Dummy question 6"}""",
}


@pytest.fixture
def faq_data(client, db_engine, refresh_end=False):
    headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
    with db_engine.connect() as db_connection:
        inbound_sql = text(insert_faq)
        for i, tags in enumerate(faq_tags):
            db_connection.execute(
                inbound_sql,
                title=f"Pytest title #{i}",
                content=f"Dummy content #{i}",
                faq_tags=tags,
                faq_contexts=faq_contexts[i],
                **faq_other_params,
            )
    client.get("/internal/refresh-faqs", headers=headers)
    yield
    with db_engine.connect() as db_connection:
        t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
        db_connection.execute(t)
    client.get("/internal/refresh-faqs", headers=headers)


@pytest.fixture
def faq_data_contexts(client_context, db_engine, refresh_end=False):
    headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
    with db_engine.connect() as db_connection:
        inbound_sql = text(insert_faq)
        for i, tags in enumerate(faq_tags):
            db_connection.execute(
                inbound_sql,
                title=f"Pytest title #{i}",
                content=f"Dummy content #{i}",
                faq_tags=tags,
                faq_contexts=faq_contexts[i],
                **faq_other_params,
            )
    client_context.get("/internal/refresh-faqs", headers=headers)
    yield
    with db_engine.connect() as db_connection:
        t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
        db_connection.execute(t)
    client_context.get("/internal/refresh-faqs", headers=headers)


class TestInboundMessage:
    def test_inbound_returns_3_faqs(self, client, faq_data):
        """
        TODO: parametrize the test based on top_n_matches
        """
        request_data = {
            "text_to_match": "I love going hiking. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()

        assert len(json_data["top_responses"]) == 3

    def test_inbound_endpoint_works_on_regular_message(self, client):
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

    def test_inbound_endpoint_works_on_empty_tokens(self, client):
        request_data = {
            "text_to_match": "?",  # gets preprocessed to []
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()
        assert "inbound_id" in json_data
        assert "scoring" in json_data
        assert "top_responses" in json_data
        assert "feedback_secret_key" in json_data

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_contextualization_active_without_context_works(
        self, faq_data_contexts, client_context
    ):
        request_data = {
            "text_to_match": "Can I enjoy movies while deploying the new version?",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client_context.post(
            "/inbound/check", json=request_data, headers=headers
        )
        json_data = response.get_json()
        assert "inbound_id" in json_data
        assert "top_responses" in json_data
        assert "feedback_secret_key" in json_data

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_contextualization_active_with_context_works(
        self, faq_data_contexts, client_context
    ):
        request_data = {
            "text_to_match": "Can I enjoy movies while deploying the new version?",
            "context": ["deploy", "maintain"],
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client_context.post(
            "/inbound/check", json=request_data, headers=headers
        )
        json_data = response.get_json()
        assert "inbound_id" in json_data
        assert "top_responses" in json_data
        assert "feedback_secret_key" in json_data

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_contextualization_inactive_with_contexts_works(self, faq_data, client):
        request_data = {
            "text_to_match": "Can I enjoy movies while deploying the new version?",
            "context": ["deploy", "maintain"],
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()
        assert "inbound_id" in json_data
        assert "top_responses" in json_data
        assert "feedback_secret_key" in json_data


@pytest.mark.slow
class TestInboundFeedback:
    insert_inbound = (
        "INSERT INTO inbounds ("
        "inbound_text, feedback_secret_key, inbound_secret_key,inbound_metadata, "
        "inbound_utc, model_scoring, returned_content, returned_utc) "
        "VALUES ('i am 12. Can i get the vaccine?', :feedback_secret_key, :inbound_secret_key,:metadata, :utc, "
        ":score, :content, :r_utc)"
    )
    inbound_other_params = {
        "feedback_secret_key": "abc123",
        "inbound_secret_key": "abc456",
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

    @pytest.fixture
    def request_json(self):
        feedback_json = {
            "inbound_id": 0,
            "feedback_secret_key": "abcde",
            "feedback": {"feedback_type": "positive", "faq_id": 3},
        }
        return feedback_json

    def test_inbound_feedback_nonexistent_id(self, client, request_json):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 404
        assert response.data == b"No Matches"

    def test_inbound_feedback_wrong_feedback_key(
        self, inbound_id, client, request_json
    ):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "wrong_secret_key",
        }
        request_json.update(request_data)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 403
        assert response.data == b"Incorrect Feedback Secret Key"

    def test_inbound_feedback_success(self, inbounds, inbound_id, client, request_json):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "abc123",
        }
        request_json.update(request_data)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 200
        assert response.data == b"Success"

    def test_inbound_feedback_success_negative(
        self, inbounds, inbound_id, client, request_json
    ):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "abc123",
            "feedback": {"feedback_type": "negative", "page_number": 3},
        }
        request_json.update(request_data)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 200
        assert response.data == b"Success"

    def test_inbound_feedback_no_faq_id(
        self, inbounds, inbound_id, client, request_json
    ):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "abc123",
            "feedback": {"feedback_type": "positive", "page_number": 10},
        }
        request_json.update(request_data)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 400
        assert response.data == b"Malformed Feedback JSON"

    def test_inbound_feedback_negative_no_page_or_faq(
        self, inbounds, inbound_id, client, request_json
    ):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "abc123",
            "feedback": {"feedback_type": "negative"},
        }
        request_json.update(request_data)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 400
        assert response.data == b"Malformed Feedback JSON"

    @pytest.mark.parametrize("feedback_type", [None, "", "funkyfeedback"])
    def test_inbound_feedack_wrong_feedback_type(
        self, inbounds, inbound_id, client, request_json, feedback_type
    ):
        request_data = {
            "inbound_id": inbound_id,
            "feedback_secret_key": "abc123",
            "feedback": {"feedback_type": feedback_type},
        }
        request_json.update(request_data)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.put("/inbound/feedback", json=request_json, headers=headers)
        assert response.status_code == 400
        assert response.data == b"Malformed Feedback JSON"


@pytest.mark.slow
class TestInboundPagination:
    @pytest.fixture
    def inbound_response_json(self, client, db_engine, faq_data):
        request_data = {
            "text_to_match": "I love going hiking. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)

        yield response.get_json()

        with db_engine.connect() as db_connection:
            t = text("DELETE FROM inbounds")
            db_connection.execute(t)

    def test_no_previous_url_for_first_page(self, inbound_response_json):
        prev_page_url = inbound_response_json.get("prev_page_url")
        assert prev_page_url is None

    def test_accessing_valid_next_page(self, client, inbound_response_json):
        next_page_url = inbound_response_json["next_page_url"]

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        page_response = client.get(next_page_url, headers=headers)
        response_json = page_response.get_json()

        assert page_response.status_code == 200
        assert inbound_response_json["inbound_id"] == response_json["inbound_id"]

        top_results_page1 = {x[0] for x in inbound_response_json["top_responses"]}
        top_results_page2 = {x[0] for x in response_json["top_responses"]}

        assert len(top_results_page1.intersection(top_results_page2)) == 0

    def test_accessing_valid_prev_page(self, client, inbound_response_json):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}

        next_page_url = inbound_response_json["next_page_url"]
        page2_response = client.get(next_page_url, headers=headers)

        prev_page_url = page2_response.get_json()["prev_page_url"]
        page1_response = client.get(prev_page_url, headers=headers)

        response_json = page1_response.get_json()

        assert inbound_response_json["top_responses"] == response_json["top_responses"]
        assert inbound_response_json["inbound_id"] == response_json["inbound_id"]
        assert response_json.get("prev_page_url") is None

    def test_no_next_url_past_max_pages(self, client, inbound_response_json):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}

        next_page_url = inbound_response_json["next_page_url"]
        page2_response = client.get(next_page_url, headers=headers)

        next_page_url = page2_response.get_json().get("next_page_url")
        assert next_page_url is None

    def test_page_does_not_exist(self, client, inbound_response_json):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}

        next_page_url = inbound_response_json["next_page_url"]
        nonexistent_page_response_url = re.sub(
            r"/inbound/([0-9]+)/[0-9]+\?(.+)$", r"/inbound/\1/9999?\2", next_page_url
        )
        nonexistent_page_response = client.get(
            nonexistent_page_response_url, headers=headers
        )

        assert nonexistent_page_response.status_code == 404
