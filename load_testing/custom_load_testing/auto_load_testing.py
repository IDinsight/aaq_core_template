import os
import shlex
import subprocess

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

hosts_dict = {
    "LOCAL_HOST": os.getenv("LOCAL_HOST"),
    "STAGING_HOST": os.getenv("STAGING_HOST"),
    "DEV_HOST": os.getenv("DEV_HOST"),
}


def run_single_test(
    host, locustfile, users, spawn_rate, run_time, output_folder, test_name
):
    """
    Runs a single locust test.

    This function takes locust parameters and runs a locust load test, saving the results to the output_folder.

    Args:
        host (str): host to test
        locustfile (str): locustfile to use
        users (int): number of users to simulate
        spawn_rate (int): number of users to spawn per second
        run_time (str): time to run the test for
        output_folder (str): The name of output folder
        test_name (str): The name of the test
    Returns:
        None
    """

    html_output = f"{output_folder}/html_reports/{test_name}_report.html"
    os.makedirs(f"{output_folder}/raw/{test_name}", exist_ok=True)
    # "test" filename is used by locust to construct test_stats.csv, test_stats_history.csv, etc.
    output_filepath = f"{output_folder}/raw/{test_name}/test"

    # run locust test
    locust_command = shlex.split(
        # Note: We are using using --autostart and --autoquit instead of --headless
        # since we want to track our tests on the webUI and the webUI must be enabled
        # for plots to be generated for the Locust HTML reports.
        f"locust --autostart --autoquit 10 \
        --host {host} --locustfile {locustfile} \
        -u {users} -r {spawn_rate} -t {run_time} \
        --csv {output_filepath} --html {html_output}"
    )
    subprocess.run(locust_command)


def run_tests(experiment_configs, output_folder):
    """
    Takes a dict of experiment parameters and cycles through all values for all parameters, running a load-test for each combination.

    Args:
        experiment_configs (dict): dict of experiment parameters, where keys are parameter names and values are lists of parameter values
        output_folder (str): The name of output folder that results should be saved to
    Returns:
        None
    """

    ### extract experiment parameter values
    host = hosts_dict[experiment_configs.get("host_label")]
    users_list = experiment_configs.get("users_list")
    # Note: default spawn rate = no. of users up to max 100 users/sec.
    default_spawn_rate_list = [min(users, 100) for users in users_list]
    spawn_rate_list = experiment_configs.get("spawn_rate_list", default_spawn_rate_list)
    run_time_list = experiment_configs.get("run_time_list")
    locustfile_list = experiment_configs.get("locustfile_list")

    ### create root results folder
    os.makedirs(output_folder, exist_ok=True)
    # create subfolder to store Locust HTML reports
    os.makedirs(output_folder + "/html_reports", exist_ok=True)

    ### Run tests, looping through given test parameters

    # loop through locustfile used (i.e. type of request sent)
    for locustfile in locustfile_list:
        # loop through number of users (+ corresponding run-time and spawn-rate)
        for users_id, users in enumerate(users_list):

            # get corresponding run-time
            run_time = run_time_list[users_id]
            # get corresponding spawn-rate
            spawn_rate = spawn_rate_list[users_id]

            locustfile_path = "locustfiles/" + locustfile
            # Construct test_name output files based on test parameters
            locustfile_no_ext = locustfile[:-3]  # remove ".py" extension
            test_name = f"{users}_user_{locustfile_no_ext}"

            print(
                f"""
                Running load-test...
                Max users: {users}
                Spawn rate: {spawn_rate}
                Locustfile: {locustfile_path}
                Runtime: {run_time}
                """
            )

            # Run load-test (also saves results to file)
            run_single_test(
                host=host,
                locustfile=locustfile_path,
                users=users,
                spawn_rate=spawn_rate,
                run_time=run_time,
                output_folder=output_folder,
                test_name=test_name,
            )

            print(f"Finished load-test {test_name}.")

    print(
        f"### All tests complete. Raw results and HTML reports saved to {output_folder} ###"
    )


def collate_and_plot_all_results(experiment_configs, output_folder):
    """
    This function loads results from previously-run tests and collates and plots them.

    Saves the following to file:
    - all_response_times_vs_time.png: Grid of plots of response times for each test vs time elapsed
    - all_reqs_per_sec_vs_time.png: Grid of plots of reqs/sec and errors/sec for each test vs time elapsed
    - endoftest_results_all.csv: results_df CSV file containing the end-of-test locust stats for each test (also returned by function)

    Args:
        experiment_configs (dict): dict of experiment parameters, where keys are parameter names and values are lists of parameter values
        output_folder (str): The name of output folder that results were saved to
    Returns:
        results_df (pd.DataFrame): dataframe containing the end-of-test locust stats for each test
    """

    ### Extract relevant config params
    users_list = experiment_configs.get("users_list")
    locustfile_list = experiment_configs.get("locustfile_list")

    ### check if test is ramped or not by checking if spawn_rate_list is given or not
    if experiment_configs.get("spawn_rate_list") is None:
        is_ramped = False
    else:
        is_ramped = True

    ### Instantiate lists to collect combined results
    result_df_list = []
    failures_df_list = []

    ### Instantiate figures for grid plots
    figsize_x = max(2.5 * len(users_list), 6)
    figsize_y = max(2.5 * len(locustfile_list), 6)

    # For response time plots
    f_rt, axes_rt = plt.subplots(
        # add extra plot to the bottom for user count over time if test is ramped
        len(locustfile_list) + is_ramped,
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey="row",
        constrained_layout=True,
    )
    f_rt.supxlabel("Seconds Elapsed")

    # For requests/s + errors/s plots
    f_reqs, axes_reqs = plt.subplots(
        # add extra plot to the bottom for user count over time if test is ramped
        len(locustfile_list) + is_ramped,
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey="row",
        constrained_layout=True,
    )
    f_reqs.supxlabel("Seconds Elapsed")

    ### Loop through all tests and collate results (imitates the loop in run_tests())
    # loop through locustfile used
    for locustfile_id, locustfile in enumerate(locustfile_list):
        # loop through number of users
        for users_id, users in enumerate(users_list):

            ### A. Collect end-of-test results for this test

            # Construct test_name based on test parameters (as done in run_tests() to match file/folder names)
            locustfile_no_ext = locustfile[:-3]  # remove ".py" extension
            test_name = f"{users}_user_{locustfile_no_ext}"
            # Read results from test_stats_history.csv from the relevant subfolder
            test_results = pd.read_csv(
                f"{output_folder}/raw/{test_name}/test_stats_history.csv"
            )
            # Create new "seconds_elapsed" variable
            test_results["Seconds Elapsed"] = (
                test_results["Timestamp"] - test_results["Timestamp"][0]
            )
            # To get end-of-test stats, select the last entry (contains stats for final 10s)
            # Note: Must manually check the test plots to make sure that the response times have flattened by this point.
            #       If they haven't, increase the run-time and re-run the load test.
            # ToDo: Automate this check. Requires a way to robustly determine when the response times have flattened.
            test_results_chosen = test_results.iloc[-1].copy()
            # add name of locustfile used to the results
            test_results_chosen.loc["locustfile"] = locustfile_no_ext
            # replace users with actual number of users (final row always has users = 0)
            test_results_chosen.loc["User Count"] = users
            # add results from this test to collated list
            result_df_list.append(test_results_chosen)

            ### B. Collect failures for this test (if any)

            # Read failures.csv from the relevant results subfolder
            test_failures = pd.read_csv(
                f"{output_folder}/raw/{test_name}/test_failures.csv", header=0
            )
            # only add test failures to list if there are any
            if not test_failures.empty:
                # add name of locustfile and n users used to the failures df
                test_failures["locustfile"] = locustfile_no_ext
                test_failures["User Count"] = users
                # add failures from this test to list
                failures_df_list.append(test_failures)

            ### C. Plots

            ## Plot Response Times vs time elapsed:
            # 50th percentile (Median)
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="50%",
                label="Median (ms)",
                legend=None,
                ax=axes_rt[locustfile_id, users_id],
            )
            # 95th percentile
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="95%",
                label="95% (ms)",
                legend=None,
                ax=axes_rt[locustfile_id, users_id],
            )
            # remove axis labels for all subplots
            axes_rt[locustfile_id, users_id].set_xlabel("")
            axes_rt[locustfile_id, users_id].set_ylabel("")
            # add number of users to top of each column
            if locustfile_id == 0:
                axes_rt[locustfile_id, users_id].set_title(f"{users} users")
            # add locustfile name to left of each row
            if users_id == 0:
                axes_rt[locustfile_id, users_id].set_ylabel(locustfile_no_ext)
            # add legend to top left plot only
            if locustfile_id == 0 and users_id == 0:
                axes_rt[locustfile_id, users_id].legend(loc="upper left")

            ## Plot Reqs/s and Errors/s vs time elapsed:
            # Reqs/s
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="Requests/s",
                label="Requests/s",
                legend=None,
                ax=axes_reqs[locustfile_id, users_id],
            )
            # Errors/s
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="Failures/s",
                label="Failures/s",
                color="red",
                legend=None,
                ax=axes_reqs[locustfile_id, users_id],
            )
            # remove axis labels for all subplots
            axes_reqs[locustfile_id, users_id].set_xlabel("")
            axes_reqs[locustfile_id, users_id].set_ylabel("")
            # add number of users to top of each column
            if locustfile_id == 0:
                axes_reqs[locustfile_id, users_id].set_title(f"{users} users")
            # add locustfile name to left of each row
            if users_id == 0:
                axes_reqs[locustfile_id, users_id].set_ylabel(locustfile_no_ext)
            # add legend to top left plot only
            if locustfile_id == 0 and users_id == 0:
                axes_reqs[locustfile_id, users_id].legend(loc="upper left")

            ## Plot user count vs time elapsed (only if test is ramped)
            # Note: This plot only needs to be added once per column, here we do this during the first locustfile iteration
            if is_ramped and locustfile_id == 0:

                # For response time plots
                sns.lineplot(
                    data=test_results,
                    x="Seconds Elapsed",
                    y="User Count",
                    label="Total Users",
                    legend=None,
                    # add plot to the bottom row of the grid
                    ax=axes_rt[-1, users_id],
                )
                # Set bottom row title
                axes_rt[-1, 0].set_xlabel("")

                # Do the same for Reqs/s and Errors/s
                sns.lineplot(
                    data=test_results,
                    x="Seconds Elapsed",
                    y="User Count",
                    label="Total Users",
                    legend=None,
                    ax=axes_reqs[-1, users_id],
                )
                # Set bottom row title
                axes_reqs[-1, 0].set_xlabel("")

    ### Make new output subfolder for processed results
    os.makedirs(output_folder + "/processed", exist_ok=True)

    ### Save plots
    print("Saving stats vs time plots for all tests...")
    f_rt.savefig(f"{output_folder}/processed/all_response_times_vs_time.png")
    f_reqs.savefig(f"{output_folder}/processed/all_reqs_per_sec_vs_time.png")

    ### Combine results into one dataframe and save to file
    results_df = pd.concat(result_df_list, axis=1).T
    # select rows to keep and reorder
    results_df = results_df[
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
    results_df.sort_values(
        by=["locustfile", "User Count"], ascending=True, inplace=True, ignore_index=True
    )
    print("Saving endoftest_results_all.csv...")
    results_df.to_csv(
        f"{output_folder}/processed/endoftest_results_all.csv", index=False
    )

    ### Combine failures into one dataframe and save to file (if any encountered)
    if len(failures_df_list) > 0:
        # combine failures into one dataframe and save to file as well
        failures_df = pd.concat(failures_df_list, axis=0)
        failures_df = failures_df[
            ["locustfile", "User Count", "Method", "Name", "Error", "Occurrences"]
        ]
        print("Saving failures_all.csv...")
        failures_df.to_csv(f"{output_folder}/processed/failures_all.csv", index=False)
    else:
        print("No failures encountered during tests. Skipping failures_all.csv.")

    return results_df


def plot_endoftest_results_vs_users(results_df, output_folder):
    """
    Plots endoftest results vs n_users for each locustfile used. Saves the following to file:

    - endoftest_response_times_vs_users.png: Response times vs. number of users per locustfile (type of request)
    - endoftest_reqs_per_sec_vs_users.png: Requests/s vs. number of users per locustfile (type of request)

    Args:
        results_df (pandas.DataFrame): Results dataframe from process_results()
        output_folder (str): Path to output folder
    Returns:
        None
    """

    ### Plot median response time vs number of users, colored by locustfile

    f, axes = plt.subplots(2, 1, figsize=(6, 6), constrained_layout=True)
    sns.lineplot(
        data=results_df,
        x="User Count",
        y="Total Median Response Time",
        hue="locustfile",
        ax=axes[0],
    )
    # zoomed-in plot
    sns.lineplot(
        data=results_df[results_df["User Count"] <= 100],
        x="User Count",
        y="Total Median Response Time",
        hue="locustfile",
        legend=None,
        ax=axes[1],
    )
    axes[1].set_title("Zoomed-in to first 100 users")
    # save plot
    plt.savefig(
        f"{output_folder}/processed/endoftest_response_times_vs_users.png", dpi=300
    )

    ### Plot max reqs/s vs number of users, colored by locustfile

    f, axes = plt.subplots(2, 1, figsize=(6, 6), constrained_layout=True)
    sns.lineplot(
        data=results_df, x="User Count", y="Requests/s", hue="locustfile", ax=axes[0]
    )
    # zoomed-in plot
    sns.lineplot(
        data=results_df[results_df["User Count"] <= 100],
        x="User Count",
        y="Requests/s",
        hue="locustfile",
        legend=None,
        ax=axes[1],
    )
    axes[1].set_title("Zoomed-in to first 100 users")
    # save plot
    plt.savefig(
        f"{output_folder}/processed/endoftest_reqs_per_sec_vs_users.png", dpi=300
    )


def calculate_endoftest_results_summary(results_df, experiment_name, output_folder):
    """
    Collects the minimum response time (mean, median) and max requests achieved by the server across any number of users, per locustfile.

    - endoftest_results_summary.csv: CSV of final combined results for each locustfile (i.e. request type)

    Args:
        results_df (pandas.DataFrame): Results dataframe from process_results()
        output_folder (str): Path to output folder
    Returns:
        results_df_summary (pandas.DataFrame): Summary dataframe of results
    """

    # Minimum response time (mean, median) and max requests achieved by the server
    results_summary = results_df.groupby("locustfile").agg(
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

    # reset index
    results_summary.reset_index(inplace=True)

    # insert experiment name column at the beginning
    results_summary.insert(0, "Experiment Name", experiment_name)

    # Save to file
    print("Saving endoftest_results_summary.csv...")
    results_summary.to_csv(
        f"{output_folder}/processed/endoftest_results_summary.csv", index=True
    )

    return results_summary


def run_all_experiments(configs, args):
    """
    Runs all experiments specified in configs and saves results to output folder.

    Args:
        configs (list): List of dicts, each dict containing the following keys:
        args (argparse.Namespace): Arguments from argparse
    Returns:
        None
    """

    # Initialize empty list to store summary results from each experiment
    results_summary_list = []

    ### Loop through each experiment and run the tests specified in its config
    for experiment_name, experiment_configs in configs.items():

        print(
            f"""
            #################################################
            ### Running experiment {experiment_name} ###
            #################################################
            """
        )

        ### Create output folder for this experiment
        output_folder = f"{args.output_folder}/{experiment_name}"

        ### Run Load Tests
        # only run new load-tests if analyze-results-only arg is not passed
        if not args.analyze_results_only:
            run_tests(
                experiment_configs=experiment_configs, output_folder=output_folder
            )

        ### Analyze Results
        # collate, plot, and save test results to file
        results_df = collate_and_plot_all_results(
            experiment_configs=experiment_configs, output_folder=output_folder
        )
        # calculate and save summary results to file
        results_summary = calculate_endoftest_results_summary(
            results_df=results_df,
            experiment_name=experiment_name,
            output_folder=output_folder,
        )
        # add summary results to list
        results_summary_list.append(results_summary)

        # plot end-of-test results vs n_users (only if more than one n_users load was tested)
        if len(experiment_configs["users_list"]) > 1:
            plot_endoftest_results_vs_users(
                results_df=results_df, output_folder=output_folder
            )

    # Combine summary results across all experiments and save to file
    print("Saving master summary - all_experiments_endoftest_results_summary.csv...")
    results_summary_df = pd.concat(results_summary_list).reset_index(drop=True)
    results_summary_df.to_csv(
        f"{args.output_folder}/all_experiments_endoftest_results_summary.csv",
        index=True,
    )
