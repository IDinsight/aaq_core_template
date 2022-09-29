import logging
import os
import shlex
import subprocess

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logging.basicConfig(level=logging.INFO)

hosts_dict = {
    "LOCAL_HOST": os.getenv("LOCAL_HOST"),
    "STAGING_HOST": os.getenv("STAGING_HOST"),
    "DEV_HOST": os.getenv("DEV_HOST"),
}


def run_single_test(
    host, locust_file, users, spawn_rate, run_time, output_folder, test_name
):
    """Runs a single locust test.

    This function takes locust parameters and runs a locust load test, saving the results to the output_folder.

    Parameters
    ----------
    host : str
        host to test
    locust_file : str
        locust_file to use
    users : int
        number of users to simulate
    spawn_rate : int
        number of users to spawn per second
    run_time : str
        time to run the test for
    output_folder : str
        Path to output folder
    test_name : str
        The name of test

    """
    html_output = f"{output_folder}/html_reports/{test_name}_report.html"
    os.makedirs(f"{output_folder}/raw/{test_name}", exist_ok=True)
    # "test" filename is used by locust as a prefix
    output_filepath = f"{output_folder}/raw/{test_name}/test"

    # run locust test
    locust_command = shlex.split(
        # Note:
        # We are using using --autostart and --autoquit instead of --headless
        # since we want to track our tests on the webUI and the webUI must be enabled
        # for plots to be generated for the Locust HTML reports.
        f"locust --autostart --autoquit 10 \
        --host {host} --locustfile {locust_file} \
        -u {users} -r {spawn_rate} -t {run_time} \
        --csv {output_filepath} --html {html_output}"
    )
    subprocess.run(locust_command)


def run_tests(experiment_configs, output_folder):
    """Takes a dict of experiment parameters and cycles through all values for all parameters, running a load-test for each combination.

    Parameters
    ----------
    experiment_configs : dict
        dict of experiment parameters from the config file
    output_folder : str
        Path to output folder

    """
    host = hosts_dict[experiment_configs.get("host_label")]
    locustfile_list = experiment_configs.get("locustfile_list")
    users_list = experiment_configs.get("users_list")
    run_time_list = experiment_configs.get("run_time_list")
    # Note: default spawn-rate = n users, up to max 100 users/sec.
    spawn_rate_list = experiment_configs.get(
        "spawn_rate_list", [min(users, 100) for users in users_list]
    )

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(output_folder + "/html_reports", exist_ok=True)

    for locust_file in locustfile_list:
        for users_id, users in enumerate(users_list):

            run_time = run_time_list[users_id]
            spawn_rate = spawn_rate_list[users_id]

            locust_file_path = "locustfiles/" + locust_file
            locust_file_no_ext = locust_file[:-3]
            test_name = f"{users}_user_{locust_file_no_ext}"

            logging.info(
                f"""
                Running load-test...
                Max users: {users}
                Spawn rate: {spawn_rate}
                locust_file: {locust_file_path}
                Runtime: {run_time}
                """
            )

            run_single_test(
                host=host,
                locust_file=locust_file_path,
                users=users,
                spawn_rate=spawn_rate,
                run_time=run_time,
                output_folder=output_folder,
                test_name=test_name,
            )

            logging.info(f"Finished load-test {test_name}.")

    logging.info(
        f"### All tests complete. Raw results and HTML reports saved to {output_folder} ###"
    )


def collate_and_plot_all_results(experiment_configs, output_folder):
    """Loads results from previously-run tests and collates and plots them.

    Saves the following to file:
    - all_response_times_vs_time.png: Grid of plots of response times for each test vs time elapsed
    - all_reqs_per_sec_vs_time.png: Grid of plots of reqs/sec and errors/sec for each test vs time elapsed
    - endoftest_results_all.csv: results_df CSV file containing the end-of-test locust stats for each test (also returned by function)

    Parameters
    ----------
    experiment_configs : dict
        dict of experiment parameters, where keys are parameter names and values are lists of parameter values
    output_folder : str
        Path to output folder

    Returns
    -------
    pd.DataFrame

    """
    users_list = experiment_configs.get("users_list")
    locustfile_list = experiment_configs.get("locustfile_list")

    # check if test is ramped or not by checking if spawn_rate_list is given or not
    if experiment_configs.get("spawn_rate_list") is None:
        is_ramped = False
    else:
        is_ramped = True

    # Instantiate lists to collect combined results
    result_df_list = []
    failures_df_list = []

    # Instantiate figures for grid plots
    figsize_x = max(2.5 * len(users_list), 6)
    figsize_y = max(2.5 * len(locustfile_list), 6)

    f_rt, axes_rt = plt.subplots(
        # if test is ramped, add extra plot to the bottom for user count over time
        len(locustfile_list) + is_ramped,
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey="row",
        constrained_layout=True,
    )
    f_rt.supxlabel("Seconds Elapsed")

    f_reqs, axes_reqs = plt.subplots(
        # if test is ramped, add extra plot to the bottom for user count over time
        len(locustfile_list) + is_ramped,
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey="row",
        constrained_layout=True,
    )
    f_reqs.supxlabel("Seconds Elapsed")

    # Loop through all tests and collate results (imitates the loop in run_tests())
    for locust_file_id, locust_file in enumerate(locustfile_list):
        for users_id, users in enumerate(users_list):

            # A. Collect end-of-test results for this test

            # Read results from test_stats_history.csv from the relevant subfolder
            locust_file_no_ext = locust_file[:-3]
            test_name = f"{users}_user_{locust_file_no_ext}"
            test_results = pd.read_csv(
                f"{output_folder}/raw/{test_name}/test_stats_history.csv"
            )
            test_results["Seconds Elapsed"] = (
                test_results["Timestamp"] - test_results["Timestamp"][0]
            )

            # To get end-of-test stats, select the last entry (contains stats for final 10s).
            # Note: Must manually check the test plots to make sure that the response times have flattened by this point.
            #       If they haven't, increase the run-time and re-run the load test.
            # To-Do: Automate this check. Requires a way to robustly determine when the response times have flattened.
            test_results_chosen = test_results.iloc[-1].copy()
            test_results_chosen.loc["locust_file"] = locust_file_no_ext
            test_results_chosen.loc["User Count"] = users  # add correct n_users info
            result_df_list.append(test_results_chosen)

            # B. Collect failures for this test (if any)

            test_failures = pd.read_csv(
                f"{output_folder}/raw/{test_name}/test_failures.csv", header=0
            )
            if not test_failures.empty:
                test_failures["locust_file"] = locust_file_no_ext
                test_failures["User Count"] = users
                failures_df_list.append(test_failures)

            # C. Plots

            # Plot Response Times vs time elapsed:
            # 50th percentile (Median)
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="50%",
                label="Median (ms)",
                legend=None,
                ax=axes_rt[locust_file_id, users_id],
            )
            # 95th percentile
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="95%",
                label="95% (ms)",
                legend=None,
                ax=axes_rt[locust_file_id, users_id],
            )
            # remove axis labels for all subplots
            axes_rt[locust_file_id, users_id].set_xlabel("")
            axes_rt[locust_file_id, users_id].set_ylabel("")
            # add number of users to top of each column
            if locust_file_id == 0:
                axes_rt[locust_file_id, users_id].set_title(f"{users} users")
            # add locust_file name to left of each row
            if users_id == 0:
                axes_rt[locust_file_id, users_id].set_ylabel(locust_file_no_ext)
            # add legend to top left plot only
            if locust_file_id == 0 and users_id == 0:
                axes_rt[locust_file_id, users_id].legend(loc="upper left")

            # Plot Reqs/s and Errors/s vs time elapsed:
            # Reqs/s
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="Requests/s",
                label="Requests/s",
                legend=None,
                ax=axes_reqs[locust_file_id, users_id],
            )
            # Errors/s
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="Failures/s",
                label="Failures/s",
                color="red",
                legend=None,
                ax=axes_reqs[locust_file_id, users_id],
            )
            # remove axis labels for all subplots
            axes_reqs[locust_file_id, users_id].set_xlabel("")
            axes_reqs[locust_file_id, users_id].set_ylabel("")
            # add number of users to top of each column
            if locust_file_id == 0:
                axes_reqs[locust_file_id, users_id].set_title(f"{users} users")
            # add locust_file name to left of each row
            if users_id == 0:
                axes_reqs[locust_file_id, users_id].set_ylabel(locust_file_no_ext)
            # add legend to top left plot only
            if locust_file_id == 0 and users_id == 0:
                axes_reqs[locust_file_id, users_id].legend(loc="upper left")

            # if test is ramped, plot user count vs time elapsed
            # Note: This plot only needs to be added once per column, hence locust_file_id == 0.
            if is_ramped and locust_file_id == 0:

                sns.lineplot(
                    data=test_results,
                    x="Seconds Elapsed",
                    y="User Count",
                    label="Total Users",
                    legend=None,
                    ax=axes_rt[-1, users_id],
                )
                axes_rt[-1, 0].set_xlabel("")

                sns.lineplot(
                    data=test_results,
                    x="Seconds Elapsed",
                    y="User Count",
                    label="Total Users",
                    legend=None,
                    ax=axes_reqs[-1, users_id],
                )
                axes_reqs[-1, 0].set_xlabel("")

    logging.info("Saving stats vs time plots for all tests...")
    os.makedirs(output_folder + "/processed", exist_ok=True)
    f_rt.savefig(f"{output_folder}/processed/all_response_times_vs_time.png")
    f_reqs.savefig(f"{output_folder}/processed/all_reqs_per_sec_vs_time.png")

    # Process final results and save to file
    results_df = pd.concat(result_df_list, axis=1).T
    results_df = results_df[
        [
            "locust_file",
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
    results_df.sort_values(
        by=["locust_file", "User Count"],
        ascending=True,
        inplace=True,
        ignore_index=True,
    )
    logging.info("Saving endoftest_results_all.csv...")
    results_df.to_csv(
        f"{output_folder}/processed/endoftest_results_all.csv", index=False
    )

    # Save failures to file (if encountered)
    if len(failures_df_list) > 0:
        failures_df = pd.concat(failures_df_list, axis=0)
        failures_df = failures_df[
            ["locust_file", "User Count", "Method", "Name", "Error", "Occurrences"]
        ]
        logging.info("Saving failures_all.csv...")
        failures_df.to_csv(f"{output_folder}/processed/failures_all.csv", index=False)
    else:
        logging.info("No failures encountered during tests. Skipping failures_all.csv.")

    return results_df


def plot_endoftest_results_vs_users(results_df, output_folder):
    """Plots endoftest results vs n_users for each locust_file used. Saves the following to file:

    - endoftest_response_times_vs_users.png: Response times vs. number of users per locust_file (type of request)
    - endoftest_reqs_per_sec_vs_users.png: Requests/s vs. number of users per locust_file (type of request)

    Parameters
    ----------
    results_df : pandas.DataFrame
        Results dataframe from process_results()
    output_folder : str
        Path to output folder

    """
    # Plot median response time vs number of users, colored by locust_file
    f, axes = plt.subplots(2, 1, figsize=(6, 6), constrained_layout=True)
    sns.lineplot(
        data=results_df,
        x="User Count",
        y="Total Median Response Time",
        hue="locust_file",
        ax=axes[0],
    )
    # zoomed-in plot
    sns.lineplot(
        data=results_df[results_df["User Count"] <= 100],
        x="User Count",
        y="Total Median Response Time",
        hue="locust_file",
        legend=None,
        ax=axes[1],
    )
    axes[1].set_title("Zoomed-in to first 100 users")
    # save plot
    plt.savefig(
        f"{output_folder}/processed/endoftest_response_times_vs_users.png", dpi=300
    )

    # Plot max reqs/s vs number of users, colored by locust_file
    f, axes = plt.subplots(2, 1, figsize=(6, 6), constrained_layout=True)
    sns.lineplot(
        data=results_df, x="User Count", y="Requests/s", hue="locust_file", ax=axes[0]
    )
    # zoomed-in plot
    sns.lineplot(
        data=results_df[results_df["User Count"] <= 100],
        x="User Count",
        y="Requests/s",
        hue="locust_file",
        legend=None,
        ax=axes[1],
    )
    axes[1].set_title("Zoomed-in to first 100 users")
    # save plot
    plt.savefig(
        f"{output_folder}/processed/endoftest_reqs_per_sec_vs_users.png", dpi=300
    )


def calculate_endoftest_results_summary(results_df, experiment_name, output_folder):
    """Collects the minimum response time (mean, median) and max requests achieved by the server across any number of users, per locust_file.

    - endoftest_results_summary.csv: CSV of final combined results for each locust_file (i.e. request type)

    Parameters
    ----------
    results_df : pandas.DataFrame
        Results dataframe from process_results()
    experiment_name : str
        Name of experiment
    output_folder : str
        Path to output folder

    Returns
    -------
    pandas.DataFrame

    """
    # Minimum response time (mean, median) and max requests achieved by the server
    results_summary = results_df.groupby("locust_file").agg(
        {
            "Requests/s": "max",
            "Total Request Count": "sum",
            "Total Failure Count": "sum",
            "Total Median Response Time": "min",
            "Total Average Response Time": "min",
        }
    )

    # Response time increase due to additional users
    # summary_df["Response Time Increase at overload (per user)"] = (results_df[results_df["User Count"]==100]["Total Median Response Time"] - results_df[results_df["User Count"]==50]["Total Median Response Time"])/49

    results_summary.rename(
        columns={
            "Requests/s": "Max Requests/s",
            "Total Median Response Time": "Minimum Median Response Time",
            "Total Average Response Time": "Minimum Average Response Time",
        },
        inplace=True,
    )

    results_summary.reset_index(inplace=True)
    results_summary.insert(0, "Experiment Name", experiment_name)

    logging.info("Saving endoftest_results_summary.csv...")
    results_summary.to_csv(
        f"{output_folder}/processed/endoftest_results_summary.csv", index=True
    )

    return results_summary


def run_all_experiments(configs, args):
    """Runs all experiments specified in configs and saves results to output folder.

    Parameters
    ----------
    configs : list of dicts
        List of dicts containing experiment configurations
    args : dict
        Arguments from argparse

    """

    results_summary_list = []
    for experiment_name, experiment_configs in configs.items():

        logging.info(
            f"""
            ####################################################
            ### Running experiment {experiment_name} ###
            ####################################################
            """
        )

        output_folder = f"{args.output}/{experiment_name}"
        if not args.analyze_results_only:
            run_tests(
                experiment_configs=experiment_configs, output_folder=output_folder
            )

        results_df = collate_and_plot_all_results(
            experiment_configs=experiment_configs, output_folder=output_folder
        )

        results_summary = calculate_endoftest_results_summary(
            results_df=results_df,
            experiment_name=experiment_name,
            output_folder=output_folder,
        )
        results_summary_list.append(results_summary)

        if len(experiment_configs["users_list"]) > 1:
            plot_endoftest_results_vs_users(
                results_df=results_df, output_folder=output_folder
            )

    # Combine summary results across all experiments and save to file
    logging.info(
        "Saving master summary - all_experiments_endoftest_results_summary.csv..."
    )
    results_summary_df = pd.concat(results_summary_list).reset_index(drop=True)
    results_summary_df.to_csv(
        f"{args.output}/all_experiments_endoftest_results_summary.csv",
        index=True,
    )
