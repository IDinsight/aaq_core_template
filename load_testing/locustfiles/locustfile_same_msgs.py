import os

import numpy as np
from locust import HttpUser, task

INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")
np.random.seed(0)


class APIUser(HttpUser):
    @task
    def ask_a_question(self):
        """
        Sends a question to the API.
        Experiment 1 - send the same question repeatedly.
        """

        question = "Test question."
        self.client.post(
            "/inbound/check",
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )
