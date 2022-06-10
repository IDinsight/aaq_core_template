"""
Validation scripts
"""
import os

import pytest
from sqlalchemy import text

import boto3
from .utils import S3_Handler
from datetime import datetime
from enum import Enum

from git import Repo
import sys

_ACTIONS = True


class Modes(Enum):
    """Models class"""

    HISTORY = 0
    LIST = 1
    COMMIT = 2


# def validate_commits(
#     df_test_source,
#     df_faq_source,
#     true_label_column,
#     query_column,
#     mode=0,
#     n_commits=5,
#     commits=None,
#     branch="main",
#     threshold_criteria=0.85,
# ):
#     """Loop through a repo object to obtain commits
#     For each commit, calculate accuracy metrics and generate report

#     Parameters
#     ----------
#     df_test_source : str
#         Location of test data
#     df_faq_source : str
#         Location of faqs
#     true_label_column : str
#         True labels column name
#     query_column : str
#         Column name for queries to test
#     mode : int, optional
#         Validation mode, by default 0
#     n_commits : int, optional
#         Number of commits to iterate, by default 5
#     commits : List[str] or str, optional
#         Input list of commits, by default None
#     branch: str, optional
#         Name of branch, by default main
#     threshold_criteria : float, optional
#         Threshold for warnings, by default 0.85

#     Returns
#     -------
#     str
#         Warning message

#     Raises
#     ------
#     Exception
#         If validation mode is unhandled
#     """

#     current_branch = os.environ["BRANCH"]
#     repo_name = os.environ["REPO"]
#     n_commits = 1

#     if _ACTIONS:

#         sys.path.append(f"/home/runner/work/{repo_name}/{repo_name}/core_model/")

#     repo = Repo("")

#     if mode == Modes.LIST.value:
#         results = []
#         for commit in commits:
#             repo.git.checkout(commit)
#             results.append(
#                 {
#                     "commit": commit,
#                     "datetime": commit.committed_datetime,
#                     "result": run_validation_scoring(
#                         df_test_source,
#                         df_faq_source,
#                         true_label_column,
#                         query_column,
#                     ),
#                 }
#             )

#     elif mode == Modes.COMMIT.value:
#         results = []
#         repo.git.checkout(commits)

#         results.append(
#             {
#                 "commit": commits,
#                 "datetime": commits.committed_datetime,
#                 "results": run_validation_scoring(
#                     df_test_source,
#                     df_faq_source,
#                     true_label_column,
#                     query_column,
#                 ),
#             }
#         )

#     elif mode == Modes.HISTORY.value:
#         latest_n_commits = list(repo.iter_commits(branch, max_count=n_commits))
#         results = []
#         for commit in latest_n_commits:
#             repo.git.checkout(commit)
#             results.append(
#                 {
#                     "commit": commit,
#                     "datetime": commit.committed_datetime,
#                     "result": run_validation_scoring(
#                         df_test_source,
#                         df_faq_source,
#                         true_label_column,
#                         query_column,
#                     ),
#                 }
#             )
#     else:
#         raise Exception("Unhandled Validation Mode")

#     message = generate_message(results, threshold_criteria)

#     return message, results


# def generate_message(results, threshold_criteria):
#     """Generate messages for validation results
#     Warning is set to threshold criteria
#     Parameters
#     ----------
#     results : List[dict]
#         List of commit validation results
#     threshold_criteria : float, 0-1
#         Accuracy cut-off for warnings
#     """

#     validation_messages = []
#     for validation_content in results:
#         if validation_content["result"]["top_3_match_accuracy"] < threshold_criteria:
#             message = """
#             [Alert] Accuracy was {accuracy} for {commit_tag} with {commit_message} on {commit_time} below threshold
#             """.format(
#                 accuracy=validation_content["result"]["top_3_match_accuracy"],
#                 commit_tag=validation_content["commit"].hexsha,
#                 commit_message=validation_content["commit"].summary,
#                 commit_time=validation_content["datetime"],
#             )
#             validation_messages.append(message)

#     message = """

#         ------Model Validation Results-----

#         {}

#         -----------------------------------

#         """.format(
#         " .\n".join(validation_messages)
#     )
#     return message


# def send_notification(
#     content="",
#     topic="arn:aws:sns:ap-south-1:678681925278:praekelt-vaccnlp-developer-notifications",
# ):
#     """
#     Function to send notification
#     """
#     # TODO this is dev only. find out notification norms
#     import boto3

#     sns = boto3.client("sns", region_name="ap-south-1")
#     sns.publish(
#         TopicArn=topic,
#         Message=content,
#         Subject="Model Validation Results {}".format(datetime.today().date()),
#     )


class TestPerformance:

    s3 = boto3.client("s3")
    s3r = boto3.resource("s3")
    # bucket = os.getenv("VALIDATION_BUCKET")
    bucket = "praekelt-static-resources"

    s3_handler = S3_Handler(s3, s3r, bucket)

    insert_faq = (
        "INSERT INTO faqmatches ("
        "faq_tags, faq_author, faq_title, faq_content_to_send, "
        "faq_added_utc, faq_thresholds) "
        "VALUES (:faq_tags, :author, :title, :content, :added_utc, :threshold)"
    )

    def get_validation_data(self):

        # prefix = self.bucket + os.getenv("VALIDATION_DATA_PREFIX")
        prefix = "validation_aaq/validation_khumo_labelled_aaq.csv"

        validation_data = self.s3_handler.load_dataframe_from_object(prefix)

        return validation_data

    def get_validation_faqs(self):

        # prefix = self.bucket + os.getenv("VALIDATION_FAQ_PREFIX")
        prefix = "validation_aaq/praekelt_mc_faqs.csv"
        # print(prefix)
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

    def test_top_3_performance(self, client, faq_data):
        validation_df = self.get_validation_data()

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
        print(top_k_accuracy)

        return top_k_accuracy
