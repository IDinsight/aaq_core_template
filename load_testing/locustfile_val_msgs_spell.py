import os
from dotenv import load_dotenv
import numpy as np
from locust import HttpUser, task, events  # , between, constant, constant_throughput

import question_loading_functions


#################### Import data ####

### Import env variables
load_dotenv(dotenv_path="../secrets/app_secrets.env", verbose=True)
INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")

#################### Run API calls ####

## Add seed for reproducibility
np.random.seed(0)

questions_df = question_loading_functions.load_questions()

class APIUser(HttpUser):

    # wait_time = constant(1)

    @task
    def ask_a_question(self):

        ### Experiment 3 - load a question from the validation dataset and add in spelling errors
        question_msg_id, question, faq_name, urgent = question_loading_functions.select_a_question(questions_df, add_typo=True)
        # print(question_msg_id, question)

        # send question to API
        response = self.client.post(
            "/inbound/check",
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )