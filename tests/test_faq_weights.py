import os

import numpy as np
import pytest
from sqlalchemy import text


class TestFaqWeights:

    insert_faq_no_weights = (
        "INSERT INTO faqmatches ("
        "faq_tags,faq_questions,faq_contexts, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags,:faq_questions,:faq_contexts,  :author, :title, :content, :added_utc, :threshold)"
    )

    insert_faq_w_weights = (
        "INSERT INTO faqmatches ("
        "faq_tags,faq_questions,faq_contexts, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds, faq_weight) "
        "VALUES (:faq_tags, :faq_questions,:faq_contexts,:author, :title, :content, :added_utc, "
        ":threshold, :faq_weight)"
    )
    faq_contexts = [
        """{"code", "deploy", "maintain"}""",
        """{"design","code","maintain"}""",
        """{ "test","deploy"}""",
        """{"design", "test", "deploy","maintain"}""",
        """{"design", "code","test"}""",
        """{"test"}""",
    ]

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
        "faq_questions": """{"Dummmy question 1", "Dummmy question 2", "Dummmy question 3", "Dummmy question 4","Dummmy question 5","Dummy question 6"}""",
        "threshold": "{0.1, 0.1, 0.1, 0.1}",
    }

    @pytest.fixture
    def faq_data_no_weights(self, client, db_engine):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq_no_weights)
            for i, tags in enumerate(self.faq_tags):
                db_connection.execute(
                    inbound_sql,
                    title=f"Pytest title #{i}",
                    faq_tags=tags,
                    faq_contexts=self.faq_contexts[i],
                    content=" ".join(tags),
                    **self.faq_other_params,
                )
        client.get("/internal/refresh-faqs", headers=headers)
        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        client.get("/internal/refresh-faqs", headers=headers)

    @pytest.fixture
    def faq_weights(self):
        return [1, 3, 3, 1, 1, 1]

    @pytest.fixture
    def faq_data_w_weights(self, client_weight, db_engine, faq_weights):
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq_w_weights)
            for i, (tags, weight) in enumerate(zip(self.faq_tags, faq_weights)):
                db_connection.execute(
                    inbound_sql,
                    title=f"Pytest title #{i}",
                    faq_tags=tags,
                    content=" ".join(tags),
                    faq_contexts=self.faq_contexts[i],
                    faq_weight=weight,
                    **self.faq_other_params,
                )
        client_weight.get("/internal/refresh-faqs", headers=headers)
        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        client_weight.get("/internal/refresh-faqs", headers=headers)

    def test_weights_correctly_calculated_no_weights(
        self, app_main, faq_data_no_weights
    ):
        weight_shares = [f.faq_weight_share for f in app_main.faqs]
        weights = [f.faq_weight for f in app_main.faqs]
        assert len(weights) == sum(weights)
        assert np.isclose(sum(weight_shares), 1)

    def test_weights_correctly_calculated_w_weights(
        self, app_weight, faq_data_w_weights, faq_weights
    ):
        weight_shares = [f.faq_weight_share for f in app_weight.faqs]
        weights = [f.faq_weight for f in app_weight.faqs]

        assert weights == faq_weights
        assert np.isclose(sum(weight_shares), 1)
        assert np.allclose(np.array(weight_shares), np.array(weights) / sum(weights))

    @pytest.fixture
    def ranks_simple_mean(self, client, faq_data_no_weights, faq_weights):
        request_data = {
            "text_to_match": "I love the outdoors. What should I pack for lunch?",
            "return_scoring": "true",
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        json_data = response.get_json()

        scores = []
        for _, details in json_data["scoring"].items():
            if isinstance(details, dict):
                scores.append(float(details["overall_score"]))
        score_ranks = np.argsort(scores)
        return score_ranks

    @pytest.fixture
    def ranks_mean_plus_weight(self, client_weight, faq_data_w_weights, faq_weights):
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
        for _, details in json_data["scoring"].items():
            if isinstance(details, dict):
                scores.append(float(details["overall_score"]))
        score_ranks = np.argsort(scores)
        return score_ranks

    def test_weights_increase_rank(
        self,
        ranks_mean_plus_weight,
        ranks_simple_mean,
    ):

        assert np.argwhere(ranks_simple_mean == 1) <= np.argwhere(
            ranks_mean_plus_weight == 1
        )
        assert np.argwhere(ranks_simple_mean == 2) <= np.argwhere(
            ranks_mean_plus_weight == 2
        )
