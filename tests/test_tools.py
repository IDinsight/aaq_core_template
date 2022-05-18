import os

import pytest
from sqlalchemy import text


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

    def test_validate_tags(self, client):
        request_data = {"tags_to_check": ["banana", "health", "fruit"]}
        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post(
            "/tools/validate-tags", json=request_data, headers=headers
        )
        json_data = response.get_json()
        assert len(json_data) == 0
