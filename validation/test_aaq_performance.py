"""
Validation scripts
"""
import os
from datetime import datetime

import boto3
import pandas as pd
import pytest
from nltk.corpus import stopwords
from sqlalchemy import text

# This is required to allow multithreading to work
stopwords.ensure_loaded()


def generate_message(result, test_params):
    """Generate messages for validation results
    Warning is set to threshold criteria
    Parameters
    ----------
    result : List[dict]
        List of commit validation results
    threshold_criteria : float, 0-1
        Accuracy cut-off for warnings
    """

    threshold_criteria = test_params["THRESHOLD_CRITERIA"]
    dataset = test_params["VALIDATION_DATA_PREFIX"]
    model = test_params.get("MATCHING_MODEL", "same as app config")

    if (os.environ.get("GITHUB_ACTIONS") == "true") & (result < threshold_criteria):

        current_branch = os.environ.get("BRANCH_NAME")
        repo_name = os.environ.get("REPO")
        commit = os.environ.get("HASH")

        val_message = (
            "[Alert] Accuracy using dataset {dataset} was:\n\n"
            "{accuracy:.2f}\n\n"
            "For commit tag = {commit_tag}\n"
            "Using model {model}\n"
            "On branch {branch}\n"
            "Repo {repo_name}\n\n"
            "The threshold criteria was {threshold_criteria}"
        ).format(
            accuracy=result,
            dataset=dataset,
            commit_tag=commit,
            model=model,
            branch=current_branch,
            repo_name=repo_name,
            threshold_criteria=threshold_criteria,
        )
    else:
        val_message = (
            "[Alert] Accuracy using dataset {dataset} was:\n\n"
            "{accuracy:.2f}\n\n"
            "Using model {model}\n"
            "The test threshold was {threshold_criteria}"
        ).format(
            accuracy=result,
            dataset=dataset,
            model=model,
            threshold_criteria=threshold_criteria,
        )

    message = """

        ------Model Validation Results-----

        {}

        -----------------------------------

        """.format(
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

    insert_faq = (
        "INSERT INTO faqmatches ("
        "faq_tags,faq_questions,faq_contexts, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags, :faq_questions,:faq_contexts,:author, :title, :content, :added_utc, :threshold)"
    )

    def get_validation_data(self, test_params):
        """
        Download validation data from s3
        """

        prefix = test_params["VALIDATION_DATA_PREFIX"]
        validation_data = pd.read_csv("s3://" + os.path.join(self.bucket, prefix))

        return validation_data

    def get_validation_faqs(self, test_params):
        """
        Download faq data from s3
        """

        prefix = test_params["VALIDATION_FAQ_PREFIX"]
        faq_df = pd.read_csv("s3://" + os.path.join(self.bucket, prefix))

        return faq_df

    def submit_one_inbound(self, row, client, test_params, contexts=False):
        """
        Single request to /inbound/check
        """
        row["contexts"] = eval(row["contexts"]) if row["contexts"] != "[None]" else []
        if contexts:
            request_data = {
                "text_to_match": str(row[test_params["QUERY_COL"]]),
                "context": row["contexts"],
                "return_scoring": "true",
            }
        else:
            request_data = {
                "text_to_match": str(row[test_params["QUERY_COL"]]),
                "return_scoring": "true",
            }

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        response = client.post("/inbound/check", json=request_data, headers=headers)
        top_responses = response.get_json()["top_responses"]
        top_faq_names = set(x[1] for x in top_responses)
        return row[test_params["TRUE_FAQ_COL"]] in top_faq_names

    @pytest.mark.filterwarnings("ignore::UserWarning")
    @pytest.fixture(scope="class")
    def faq_data(self, client, db_engine, test_params):

        self.faq_df = self.get_validation_faqs(test_params)

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:

            # First, delete any stragglers in the DB from previous runs
            t = text("DELETE FROM faqmatches WHERE faq_author='Validation author'")
            with db_connection.begin():
                db_connection.execute(t)

            inbound_sql = text(self.insert_faq)
            inserts = [
                {
                    "title": row["faq_title"],
                    "faq_tags": row["faq_tags"],
                    "faq_questions": """{"Dummmy question 1", "Dummmy question 2", "Dummmy question 3", "Dummmy question 4","Dummmy question 5","Dummy question 6"}""",
                    "added_utc": "2022-04-14",
                    "author": "Validation author",
                    "content": row["faq_content_to_send"],
                    "faq_contexts": row["faq_contexts"],
                    "threshold": "{0.1, 0.1, 0.1, 0.1}",
                }
                for idx, row in self.faq_df.iterrows()
            ]

            # We do a bulk insert to be more efficient
            with db_connection.begin():
                db_connection.execute(inbound_sql, inserts)
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

    def test_top_k_performance(self, client, faq_data, test_params):
        """
        Test if top k faqs contain the true FAQ
        """

        validation_df = self.get_validation_data(test_params)
        validation_df_addressed = validation_df.query("is_concern_addressed=='Yes'")
        validation_df_non_addressed = validation_df.query("is_concern_addressed=='No'")

        def submit_one_inbound(x):
            return self.submit_one_inbound(x, client, test_params)

        results_addressed = validation_df_addressed.apply(
            submit_one_inbound, axis=1
        ).tolist()
        top_k_accuracy_addressed = sum(results_addressed) / len(results_addressed)
        content_addressed = generate_message(top_k_accuracy_addressed, test_params)

        results_non_addressed = validation_df_non_addressed.apply(
            submit_one_inbound, axis=1
        ).tolist()
        top_k_accuracy_non_addressed = sum(results_non_addressed) / len(
            results_non_addressed
        )
        content_non_addressed = generate_message(
            top_k_accuracy_non_addressed, test_params
        )

        if (os.environ.get("GITHUB_ACTIONS") == "true") & (
            top_k_accuracy_addressed < test_params["THRESHOLD_CRITERIA"]
        ):
            send_notification(content_addressed)
        print(
            "-------------------Results for questions that were addressed ----------------"
        )
        print(content_addressed)
        print(
            "-------------------Results for questions that were NOT addressed ----------------"
        )
        print(content_non_addressed)

        return top_k_accuracy_addressed

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_top_k_performance_contexts(self, client, faq_data, test_params):
        """
        Test if top k faqs contain the true FAQ
        """

        validation_df = self.get_validation_data(test_params)
        validation_df_addressed = validation_df.query("is_concern_addressed=='Yes'")
        validation_df_non_addressed = validation_df.query("is_concern_addressed=='No'")

        def submit_one_inbound(x):
            return self.submit_one_inbound(x, client, test_params, True)

        results_addressed = validation_df_addressed.apply(
            submit_one_inbound, axis=1
        ).tolist()
        top_k_accuracy_addressed = sum(results_addressed) / len(results_addressed)
        content_addressed = generate_message(top_k_accuracy_addressed, test_params)

        results_non_addressed = validation_df_non_addressed.apply(
            submit_one_inbound, axis=1
        ).tolist()
        top_k_accuracy_non_addressed = sum(results_non_addressed) / len(
            results_non_addressed
        )
        content_non_addressed = generate_message(
            top_k_accuracy_non_addressed, test_params
        )

        if (os.environ.get("GITHUB_ACTIONS") == "true") & (
            top_k_accuracy_addressed < test_params["THRESHOLD_CRITERIA"]
        ):
            send_notification(content_addressed)
        print(
            "-------------------Results for questions that were addressed ----------------"
        )
        print(content_addressed)
        print(
            "-------------------Results for questions that were NOT addressed ----------------"
        )
        print(content_non_addressed)

        return top_k_accuracy_addressed
