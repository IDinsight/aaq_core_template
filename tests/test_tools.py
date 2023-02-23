import os
import pytest


@pytest.fixture
def refresh(client_context):
    headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
    client_context.get("/internal/refresh-faqs", headers=headers)
    yield


class TestNewTagTool:
    def test_check_new_tags(self, client):
        request_data = {
            "tags_to_check": ["banana", "health", "fruit"],
            "queries_to_check": [
                "Is the fruit that's long and yellow healthy",
                "nutrition facts for bananas",
            ],
        }
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post(
            "/tools/check-new-tags", json=request_data, headers=headers
        )
        json_data = response.get_json()
        assert "top_matches_for_each_query" in json_data
        assert len(json_data["top_matches_for_each_query"]) == 2
        assert (
            json_data["top_matches_for_each_query"][0][0][0]
            == "*** NEW TAGS MATCHED ***"
        )
        assert (
            json_data["top_matches_for_each_query"][1][0][0]
            == "*** NEW TAGS MATCHED ***"
        )

    def test_validate_tags(self, client):
        request_data = {"tags_to_check": ["banana", "health", "fruit"]}
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post(
            "/tools/validate-tags", json=request_data, headers=headers
        )
        json_data = response.get_json()
        assert len(json_data) == 0

    @pytest.mark.filterwarnings("ignore::UserWarning")
    @pytest.mark.parametrize(
        "contexts,is_context_valid",
        [
            (["maintain"], True),
            (["test", "deploy"], True),
            ([], True),
            (["eat"], False),
            (["eat", "maintain"], False),
        ],
    )
    def test_check_contexts_works(
        self,
        contexts,
        is_context_valid,
        refresh,
        client_context,
    ):
        request_data = {"contexts_to_check": contexts}
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client_context.post(
            "/tools/check-contexts", json=request_data, headers=headers
        )
        json_data = response.get_json()
        if is_context_valid:
            assert len(json_data) == 0
        else:
            assert len(json_data) > 0
