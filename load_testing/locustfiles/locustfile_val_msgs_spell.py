import os
import sys

import numpy as np
from custom_load_testing.question_import import load_questions, select_a_question
from locust import HttpUser, task

INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")

abs_filepath = sys.path[0] + "/../../data/validation_khumo_labelled_aaq.csv"
questions_df = load_questions(abs_filepath)
np.random.seed(0)


class APIUser(HttpUser):
    @task
    def ask_a_question(self):
        """
        Sends a question to the API.
        Experiment 3 - load a question from the validation dataset and add in spelling errors.
        """
        question = select_a_question(questions_df, add_typo=True)
        self.client.post(
            "/inbound/check",
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )
