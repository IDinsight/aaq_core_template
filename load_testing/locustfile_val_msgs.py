import os
from dotenv import load_dotenv
import numpy as np
from locust import HttpUser, task  # , between, constant, constant_throughput

### load custom functions for loading questions from file
import question_loading_functions

### Import env variables
load_dotenv(dotenv_path="../secrets/app_secrets.env", verbose=True)
INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")

### Assign data path to be used for loading the question
data_path = "../data/validation_khumo_labelled_aaq.csv"

### Run API calls
# Add seed for reproducibility
np.random.seed(0)
# import df of real-world questions
questions_df = question_loading_functions.load_questions(data_path)


class APIUser(HttpUser):
    @task
    def ask_a_question(self):
        ### Experiment 2 - load a question from the validation dataset
        (
            question_msg_id,
            question,
            faq_name,
            urgent,
        ) = question_loading_functions.select_a_question(questions_df, add_typo=False)
        # send question to API
        self.client.post(
            "/inbound/check",
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )
