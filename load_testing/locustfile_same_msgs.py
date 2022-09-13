import os
from dotenv import load_dotenv
import numpy as np
from locust import HttpUser, task  # , events, between, constant, constant_throughput

#################### Import data ####

### Import env variables
load_dotenv(dotenv_path="../secrets/app_secrets.env", verbose=True)
INBOUND_CHECK_TOKEN = os.getenv("INBOUND_CHECK_TOKEN")

#################### Run API calls ####

## Add seed for reproducibility
np.random.seed(0)

class APIUser(HttpUser):

    # wait_time = constant(1)

    @task
    def ask_a_question(self):

        ### Experiment 1 - same message sent repeatedly
        question = "is it normal to vomit every day for a week"
        # print(question_msg_id, question)

        # send question to API
        response = self.client.post(
            "/inbound/check",  # set host to "http://13.246.32.186:9902" in config
            json={"text_to_match": question, "return_scoring": "false"},
            headers={"Authorization": f"Bearer {INBOUND_CHECK_TOKEN}"},
        )