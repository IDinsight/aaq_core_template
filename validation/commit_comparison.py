"""
Main script called by Github Actions for validation
"""
from validation_functions import run_validation_scoring

import sys
from datetime import datetime
from enum import Enum

from git import Repo

_ACTIONS = True


class Modes(Enum):
    """Models class"""

    HISTORY = 0
    LIST = 1
    COMMIT = 2


def validate_commits(
    repo,
    df_test_source,
    df_faq_source,
    true_label_column,
    query_column,
    mode=0,
    n_commits=5,
    commits=None,
    branch="main",
    threshold_criteria=0.85,
):
    """Loop through a repo object to obtain commits
    For each commit, calculate accuracy metrics and generate report

    Parameters
    ----------
    repo : git.Repo
        Git repo object
    df_test_source : str
        Location of test data
    df_faq_source : str
        Location of faqs
    true_label_column : str
        True labels column name
    query_column : str
        Column name for queries to test
    mode : int, optional
        Validation mode, by default 0
    n_commits : int, optional
        Number of commits to iterate, by default 5
    commits : List[str] or str, optional
        Input list of commits, by default None
    branch: str, optional
        Name of branch, by default main
    threshold_criteria : float, optional
        Threshold for warnings, by default 0.85

    Returns
    -------
    str
        Warning message

    Raises
    ------
    Exception
        If validation mode is unhandled
    """

    if mode == Modes.LIST.value:
        results = []
        for commit in commits:
            repo.git.checkout(commit)
            results.append(
                {
                    "commit": commit,
                    "datetime": commit.committed_datetime,
                    "result": run_validation_scoring(
                        df_test_source,
                        df_faq_source,
                        true_label_column,
                        query_column,
                    ),
                }
            )

    elif mode == Modes.COMMIT.value:
        results = []
        repo.git.checkout(commits)

        results.append(
            {
                "commit": commits,
                "datetime": commits.committed_datetime,
                "results": run_validation_scoring(
                    df_test_source,
                    df_faq_source,
                    true_label_column,
                    query_column,
                ),
            }
        )

    elif mode == Modes.HISTORY.value:
        latest_n_commits = list(repo.iter_commits(branch, max_count=n_commits))
        results = []
        for commit in latest_n_commits:
            repo.git.checkout(commit)
            results.append(
                {
                    "commit": commit,
                    "datetime": commit.committed_datetime,
                    "result": run_validation_scoring(
                        df_test_source,
                        df_faq_source,
                        true_label_column,
                        query_column,
                    ),
                }
            )
    else:
        raise Exception("Unhandled Validation Mode")

    message = generate_message(results, threshold_criteria)

    return message, results


def generate_message(results, threshold_criteria):
    """Generate messages for validation results
    Warning is set to threshold criteria
    Parameters
    ----------
    results : List[dict]
        List of commit validation results
    threshold_criteria : float, 0-1
        Accuracy cut-off for warnings
    """

    validation_messages = []
    for validation_content in results:
        if validation_content["result"]["top_3_match_accuracy"] < threshold_criteria:
            message = """
            [Alert] Accuracy was {accuracy} for {commit_tag} with {commit_message} on {commit_time} below threshold
            """.format(
                accuracy=validation_content["result"]["top_3_match_accuracy"],
                commit_tag=validation_content["commit"].hexsha,
                commit_message=validation_content["commit"].summary,
                commit_time=validation_content["datetime"],
            )
            validation_messages.append(message)

    message = """

        ------Model Validation Results-----

        {}

        -----------------------------------

        """.format(
        " .\n".join(validation_messages)
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


if __name__ == "__main__":

    token = sys.argv[1]
    current_branch = sys.argv[2]
    repo_name = sys.argv[3]
    n_commits = 1

    if _ACTIONS:

        sys.path.append(f"/home/runner/work/{repo_name}/{repo_name}/core_model/")

    repo = Repo("")

    print("Running validations on ", current_branch)

    labelled_validation_data = ""
    val_faqs = ""
    actual_label_col = ""
    query_col = ""

    message, results = validate_commits(
        repo,
        labelled_validation_data,
        val_faqs,
        actual_label_col,
        query_col,
        threshold_criteria=0.95,
        branch=current_branch,
        n_commits=n_commits,
    )
    # print(message)
    # print("Validations completed!", "Sending notifications")
    # send_notification(message)

    send_notification(content="Hi")
