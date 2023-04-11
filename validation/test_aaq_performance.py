"""
Validation scripts
"""
import os
from datetime import datetime

import boto3
import numpy as np
import pandas as pd
import pytest
from nltk.corpus import stopwords
from sqlalchemy import text

# This is required to allow multithreading to work
stopwords.ensure_loaded()


def generate_message(top_k_accuracies, test_params):
    """Generate messages for validation results
    Warning is set to threshold criteria
    Parameters
    ----------
    top_k_accuracies : Dict
        Dictionary of top k accuracies, with k as keys
    threshold_criteria : float, 0-1
        Accuracy cut-off for warnings
    """

    threshold_criteria = test_params["THRESHOLD_CRITERIA"]
    dataset = test_params["VALIDATION_DATA_PREFIX"]
    model = test_params.get("MATCHING_MODEL", "same as app config")

    top_k_accuracy = top_k_accuracies[max(top_k_accuracies.keys())]
    accuracy_str = "\n".join(
        [f"Top {k}: {acc:.3f}" for k, acc in top_k_accuracies.items()]
    )

    if (os.environ.get("GITHUB_ACTIONS") == "true") & (
        top_k_accuracy < threshold_criteria
    ):

        current_branch = os.environ.get("BRANCH_NAME")
        repo_name = os.environ.get("REPO")
        commit = os.environ.get("HASH")

        val_message = (
            "[Alert] Top K accuracies using dataset {dataset} was:\n\n"
            "{accuracy}\n\n"
            "For commit tag = {commit_tag}\n"
            "Using model {model}\n"
            "On branch {branch}\n"
            "Repo {repo_name}\n\n"
            "The threshold criteria was {threshold_criteria}"
        ).format(
            dataset=dataset,
            accuracy=accuracy_str,
            commit_tag=commit,
            model=model,
            branch=current_branch,
            repo_name=repo_name,
            threshold_criteria=threshold_criteria,
        )
    else:
        val_message = (
            "[Alert] Top K accuracies using dataset {dataset} was:\n\n"
            "{accuracy}\n\n"
            "Using model {model}\n"
            "The test threshold was {threshold_criteria}"
        ).format(
            dataset=dataset,
            accuracy=accuracy_str,
            model=model,
            threshold_criteria=threshold_criteria,
        )

    message = """
------------Model Validation Results-----------

{}

-----------------------------------------------""".format(
        val_message
    )
    return message


def send_notification(
    content="",
    topic="arn:aws:sns:ap-south-1:678681925278:praekelt-vaccnlp-developer-notifications",
):
    """
    Function to send notification
    """
    sns = boto3.client("sns", region_name="ap-south-1")
    sns.publish(
        TopicArn=topic,
        Message=content,
        Subject="Model Validation Results {}".format(datetime.today().date()),
    )


class TestPerformance:

    s3 = boto3.client("s3")
    s3r = boto3.resource("s3")
    bucket = os.getenv("VALIDATION_BUCKET")

    def get_validation_data(self, test_params):
        """
        Download validation data from s3
        """

        prefix = test_params["VALIDATION_DATA_PREFIX"]
        validation_data = pd.read_csv("s3://" + os.path.join(self.bucket, prefix))

        valid_mask = (
            validation_data[
                [test_params["QUERY_COL"], test_params["FAQ_COLUMN_MAP"]["faq_title"]]
            ]
            .notnull()
            .all(axis=1)
        )

        return validation_data[valid_mask]

    def get_validation_faqs(self, test_params):
        """
        Download faq data from s3
        """

        prefix = test_params["VALIDATION_FAQ_PREFIX"]
        faq_df = pd.read_csv("s3://" + os.path.join(self.bucket, prefix))

        return faq_df

    def submit_one_inbound(self, row, client, test_params):
        """
        Single request to /inbound/check
        """
        request_data = {
            "text_to_match": str(row[test_params["QUERY_COL"]]),
            "return_scoring": "true",
        }

        if test_params["contextualization"]["active"]:
            user_contexts = eval(row["contexts"]) if row["contexts"] != "[None]" else []
            request_data["context"] = user_contexts

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        top_responses = response.get_json()["top_responses"]

        for i, res in enumerate(top_responses):
            if row[test_params["FAQ_COLUMN_MAP"]["faq_title"]] == res[1]:
                return i + 1

        return np.inf

    @pytest.mark.filterwarnings("ignore::UserWarning")
    @pytest.fixture(scope="class")
    def faq_data(self, client, db_engine, test_params):

        self.faq_df = self.get_validation_faqs(test_params)

        column_map = test_params["FAQ_COLUMN_MAP"]

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}

        with db_engine.connect() as db_connection:

            # First, delete any stragglers in the DB from previous runs
            t = text("DELETE FROM faqmatches WHERE faq_author='Validation author'")
            with db_connection.begin():
                db_connection.execute(t)

            # Map the relevant columns in the validation data to the faqmatches table columns
            rename_map = {
                column_map["faq_title"]: "faq_title",
                column_map["faq_tags"]: "faq_tags",
                column_map["faq_content_to_send"]: "faq_content_to_send",
            }

            assign_map = dict(
                faq_questions="{"
                + ", ".join([f'"Placeholder question {i}"' for i in range(1, 6)])
                + "}",
                faq_added_utc="2022-04-14",
                faq_author="Validation author",
                faq_thresholds="{0.1, 0.1, 0.1, 0.1}",
                faq_contexts="{" + ",".join(client.application.context_list) + "}",
            )

            if test_params["contextualization"]["active"]:
                rename_map[column_map["faq_contexts"]] = "faq_contexts"
                del assign_map["faq_contexts"]

            faqs_to_insert = (
                self.faq_df[rename_map.keys()]
                .rename(
                    columns=rename_map,
                )
                .copy()
            )
            faqs_to_insert = faqs_to_insert.assign(**assign_map)

            faqs_to_insert.to_sql(
                name="faqmatches",
                con=db_connection,
                if_exists="append",
                index=False,
            )

        client.get("/internal/refresh-faqs", headers=headers)
        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches WHERE faq_author='Validation author'")
            t2 = text("DELETE FROM inbounds")
            with db_connection.begin():
                db_connection.execute(t)
            with db_connection.begin():
                db_connection.execute(t2)

        client.get("/internal/refresh-faqs", headers=headers)

    def _get_top_k_accuracies(self, ranks, max_k):
        """Return a dictionary of top k accuracies for a given list of ranks"""

        top_k_accuracies = {}

        ks = [1, 3, 5, 7, 10]
        ks = [k for k in ks if k < max_k] + [max_k]
        for k in ks:
            top_k_accuracies[k] = sum(x < k for x in ranks) / len(ranks)

        return top_k_accuracies

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_top_k_performance(self, client, faq_data, test_params):
        """
        Test if top k faqs contain the true FAQ
        """

        validation_df = self.get_validation_data(test_params)

        def submit_one_inbound(x):
            return self.submit_one_inbound(x, client, test_params)

        n_top_matches = client.application.config["N_TOP_MATCHES_PER_PAGE"]
        threshold = test_params["THRESHOLD_CRITERIA"]

        filter_mask = np.ones(len(validation_df), dtype=bool)
        for col, val in test_params["TRUE_FAQ_FILTER_CONDITIONS"].items():
            filter_mask = filter_mask & (validation_df[col] == val)
        validation_df_filtered = validation_df[filter_mask].copy()

        true_faqs_rank = validation_df_filtered.apply(
            submit_one_inbound, axis=1
        ).tolist()
        top_k_accuracies_addressed = self._get_top_k_accuracies(
            true_faqs_rank, max_k=n_top_matches
        )
        notification_msg_addressed = generate_message(
            top_k_accuracies_addressed, test_params
        )

        all_faqs_rank = validation_df.apply(submit_one_inbound, axis=1).tolist()
        top_k_accuracies_all = self._get_top_k_accuracies(
            all_faqs_rank, max_k=n_top_matches
        )
        notification_msg_all = generate_message(top_k_accuracies_all, test_params)

        if (os.environ.get("GITHUB_ACTIONS") == "true") & (
            top_k_accuracies_addressed[n_top_matches] < threshold
        ):
            send_notification(notification_msg_addressed)

        msg_to_print = f"Results for true FAQs:\n\n{notification_msg_addressed}\n\n\nResults for all FAQs:\n\n{notification_msg_all}"
        print(msg_to_print)

        return top_k_accuracies_addressed
