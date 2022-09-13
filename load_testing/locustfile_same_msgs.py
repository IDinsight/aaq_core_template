import os
from dotenv import load_dotenv
import numpy as np
from locust import HttpUser, task  # , between, constant, constant_throughput

### Import env variables
load_dotenv(dotenv_path="../secrets/app_secrets.env", verbose=True)
INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")

### Run API calls
# Add seed for reproducibility
np.random.seed(0)


class APIUser(HttpUser):
    @task
    def ask_a_question(self):
        ### Experiment 1 - same message sent repeatedly
        question = "Test question."
        # send question to API
        self.client.post(
            "/inbound/check",
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )
