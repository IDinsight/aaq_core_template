import os

import numpy as np
import pytest
from sqlalchemy import text


class TestFaqWeights:

    insert_faq_no_weights = (
        "INSERT INTO faqmatches ("
        "faq_tags, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags, :author, :title, :content, :added_utc, :threshold)"
    )

    insert_faq_w_weights = (
        "INSERT INTO faqmatches ("
        "faq_tags, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds, faq_weight) "
        "VALUES (:faq_tags, :author, :title, :content, :added_utc, "
        ":threshold, :faq_weight)"
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
    def faq_data_no_weights(self, client, db_engine):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq_no_weights)
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

    @pytest.fixture
    def faq_weights(self):
        return [1, 3, 3, 1, 1, 1]

    @pytest.fixture
    def faq_data_w_weights(self, client, db_engine, faq_weights):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq_w_weights)
            for i, (tags, weight) in enumerate(zip(self.faq_tags, faq_weights)):
                db_connection.execute(
                    inbound_sql,
                    title=f"Pytest title #{i}",
                    faq_tags=tags,
                    faq_weight=weight,
                    **self.faq_other_params,
                )
        client.get("/internal/refresh-faqs", headers=headers)
        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        client.get("/internal/refresh-faqs", headers=headers)

    def test_weights_correctly_calculated_no_weights(self, app, faq_data_no_weights):
        weight_shares = [f.faq_weight_share for f in app.faqs]
        weights = [f.faq_weight for f in app.faqs]

        assert len(weights) == sum(weights)
        assert np.isclose(sum(weight_shares), 1)

    def test_weights_correctly_calculated_w_weights(
        self, app, faq_data_w_weights, faq_weights
    ):
        weight_shares = [f.faq_weight_share for f in app.faqs]
        weights = [f.faq_weight for f in app.faqs]

        assert weights == faq_weights
        assert np.isclose(sum(weight_shares), 1)
        assert np.allclose(np.array(weight_shares), np.array(weights) / sum(weights))

    def test_simple_mean_is_used(self, client, faq_data_w_weights, faq_weights):
        request_data = {
            "text_to_match": "I love the outdoors. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()

        scores = []
        for faq_id, details in json_data["scoring"].items():
            if isinstance(details, dict):
                scores.append(float(details["overall_score"]))

        score_ranks = np.argsort(scores)

        assert np.argwhere(score_ranks == 1).squeeze() == 5
        assert np.argwhere(score_ranks == 2).squeeze() != 4

    def test_mean_plus_weight_is_used(
        self, client_weight, faq_data_w_weights, faq_weights
    ):
        request_data = {
            "text_to_match": "I love the outdoors. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client_weight.post(
            "/inbound/check", json=request_data, headers=headers
        )
        json_data = response.get_json()

        scores = []
        for faq_id, details in json_data["scoring"].items():
            if isinstance(details, dict):
                scores.append(float(details["overall_score"]))

        score_ranks = np.argsort(scores)
        assert np.argwhere(score_ranks == 1).squeeze() == 5
        assert np.argwhere(score_ranks == 2).squeeze() == 4
