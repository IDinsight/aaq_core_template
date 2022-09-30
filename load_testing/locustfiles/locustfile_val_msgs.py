import os
from pathlib import Path

import numpy as np
from custom_load_testing.question_import import load_questions, select_a_question
from locust import HttpUser, task

INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")
DATA_FILE = os.getenv("LOADTEST_DATA_FILE")
SEED = 0

np.random.seed(SEED)
data_path = Path(__file__).parents[2] / "data" / DATA_FILE
questions_df = load_questions(data_path)


class APIUser(HttpUser):
    @task
    def ask_a_question(self):
        """Sends a question to the API.

        Experiment 2 - load a question from the validation dataset.

        """
        question = select_a_question(questions_df, add_typo=False)
        self.client.post(
            "/inbound/check",
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )
