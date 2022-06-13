"""
Validation scripts
"""
import os

import pytest
from sqlalchemy import text

import boto3
from .utils import S3_Handler
from datetime import datetime


def generate_message(result, threshold_criteria):
    """Generate messages for validation results
    Warning is set to threshold criteria
    Parameters
    ----------
    result : List[dict]
        List of commit validation results
    threshold_criteria : float, 0-1
        Accuracy cut-off for warnings
    """
    current_branch = os.environ["BRANCH"]
    repo_name = os.environ["REPO"]
    commit = os.environ["HASH"]
    ref = os.environ["REF"]

    if result < threshold_criteria:
        val_message = """
        [Alert] Accuracy was {accuracy} for {commit_tag} with {commit_message} on branch {branch} of repo {repo_name} below threshold of {threshold_criteria}
         """.format(
            accuracy=result,
            commit_tag=commit,
            commit_message=ref,
            branch=current_branch,
            repo_name=repo_name,
        )

    message = """

        ------Model Validation Results-----

        {}

        -----------------------------------

        """.format(
        " .\n".join(val_message)
    )
    return message


def send_notification(
    content="",
    topic="arn:aws:sns:ap-south-1:678681925278:praekelt-vaccnlp-developer-notifications",
):
    """
    Function to send notification
    """
    # TODO this is dev only. find out notification norms
    import boto3

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

    s3_handler = S3_Handler(s3, s3r, bucket)

    insert_faq = (
        "INSERT INTO faqmatches ("
        "faq_tags, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags, :author, :title, :content, :added_utc, :threshold)"
    )

    def get_validation_data(self):

        prefix = os.getenv("VALIDATION_DATA_PREFIX")

        validation_data = self.s3_handler.load_dataframe_from_object(prefix)

        return validation_data

    def get_validation_faqs(self):

        prefix = os.getenv("VALIDATION_FAQ_PREFIX")

        faq_df = self.s3_handler.load_dataframe_from_object(prefix)

        return faq_df

    @pytest.fixture
    def faq_data(self, client, db_engine):

        self.faq_df = self.get_validation_faqs()

        headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
        with db_engine.connect() as db_connection:
            inbound_sql = text(self.insert_faq)
            for i, row in self.faq_df.iterrows():
                db_connection.execute(
                    inbound_sql,
                    title=row["faq_title"],
                    faq_tags=row["faq_tags"],
                    added_utc="2022-04-14",
                    author="Pytest author",
                    content="{}",
                    threshold="{0.1, 0.1, 0.1, 0.1}",
                )
        client.get("/internal/refresh-faqs", headers=headers)
        yield
        with db_engine.connect() as db_connection:
            t = text("DELETE FROM faqmatches " "WHERE faq_author='Pytest author'")
            db_connection.execute(t)
        client.get("/internal/refresh-faqs", headers=headers)

    def test_top_3_performance(self, client, faq_data, test_params):
        validation_df = self.get_validation_data().sample(100)

        for idx, row in validation_df.iterrows():
            request_data = {
                "text_to_match": str(row["Question"]),
                "return_scoring": "true",
            }
            headers = {"Authorization": "Bearer %s" % os.getenv("INBOUND_CHECK_TOKEN")}
            response = client.post("/inbound/check", json=request_data, headers=headers)
            top_faq_names = [x[0] for x in response.get_json()["top_responses"]]
            validation_df.loc[idx, "in_top"] = row["FAQ Name"] in top_faq_names

        top_k_accuracy = validation_df["in_top"].mean()
        send_notification(
            content=generate_message(top_k_accuracy, test_params["THRESHOLD_CRITERIA"])
        )

        return top_k_accuracy
