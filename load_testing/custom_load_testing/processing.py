import pandas as pd


def get_test_result_folder_path(locustfile_no_ext, users, output_folder):
    """Constructs output folder path for a given test."""
    test_name = f"{users}_user_{locustfile_no_ext}"
    return f"{output_folder}/raw/{test_name}/"


def process_test_result(test_stats_history, locustfile, users):
    """Extracts the end-of-test result from locust test_stats_history.csv dataframe.

    To get end-of-test stats, we select the last entry which contains stats
    for the final 10s of the test.

    Note:
    Must manually check the test plots to make sure that the response times
    have flattened by this point. If they haven't, increase the run-time
    and re-run the load test.

    To-Do:
    Automate this check. Requires a way to robustly determine when the
    response times have flattened.

    Parameters
    ----------
    test_stats_history : pandas.DataFrame
        dataframe containing locust test results
    locustfile : str
        locustfile used for the test
    users : int
        number of users used for the test

    Returns
    -------
    final_test_result : pandas.Series
        series containing end-of-test result

    """
    test_stats_history["Seconds Elapsed"] = (
        test_stats_history["Timestamp"] - test_stats_history["Timestamp"][0]
    )

    final_test_result = test_stats_history.iloc[-1].copy()
    final_test_result.loc["locustfile"] = locustfile[:-3]  # removes .py extension
    final_test_result.loc["User Count"] = users  # add correct n_users info

    return final_test_result


def combine_final_test_results(final_test_results_list):
    """Combines the results from all tests into a single dataframe.

    Parameters
    ----------
    final_test_results_list : list of pandas.Series
        list of series containing end-of-test results

    Returns
    -------
    final_test_results : pandas.DataFrame

    """

    final_test_results = pd.concat(final_test_results_list, axis=1).T
    final_test_results = final_test_results[
        [
            "locustfile",
            "User Count",
            "Total Request Count",
            "Total Failure Count",
            "Requests/s",
            "Total Median Response Time",
            "Total Average Response Time",
            "Total Min Response Time",
            "Total Max Response Time",
            "Total Average Content Size",
            "50%",
            "66%",
            "75%",
            "80%",
            "90%",
            "95%",
            "98%",
            "99%",
            "99.9%",
            "99.99%",
            "100%",
        ]
    ]
    final_test_results.sort_values(
        by=["locustfile", "User Count"],
        ascending=True,
        inplace=True,
        ignore_index=True,
    )

    return final_test_results


def calculate_per_experiment_results(
    final_test_results,
    experiment_name,
):
    """
    For each locustfile used, calculates the minimimum response time and
    max reqs/s achieved by the server across all tests for that locustfile.

    To-Do:
    - Calculate the average response time increase per additional user

    Parameters
    ----------
    final_test_results : pandas.DataFrame
        Results dataframe from process_results()
    experiment_name : str
        Name of experiment

    Returns
    -------
    experiment_results : pandas.DataFrame

    """
    experiment_results = final_test_results.groupby("locustfile").agg(
        {
            "Requests/s": "max",
            "Total Request Count": "sum",
            "Total Failure Count": "sum",
            "Total Median Response Time": "min",
            "Total Average Response Time": "min",
        }
    )

    # Response time increase per additional user
    # experiment_results["Response Time Increase at overload (per user)"] = (
    # final_test_results[final_test_results["User Count"]==100]["Total Median Response Time"]
    # - final_test_results[final_test_results["User Count"]==50]["Total Median Response Time"]
    # )/49

    experiment_results.rename(
        columns={
            "Requests/s": "Max Requests/s",
            "Total Median Response Time": "Minimum Median Response Time",
            "Total Average Response Time": "Minimum Average Response Time",
        },
        inplace=True,
    )

    experiment_results.reset_index(inplace=True)
    experiment_results.insert(0, "Experiment Name", experiment_name)

    return experiment_results


def combine_experiment_results(experiment_results_list):
    """Combines results from multiple experiments into a single dataframe."""
    all_experiments_results = pd.concat(experiment_results_list).reset_index(drop=True)
    return all_experiments_results
