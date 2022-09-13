"""
This script loads a config file, runs multiple locust load tests, plots and writes results to file.
Based on: github.com/mohsenSy/locust-tests-runner/blob/master/locust_run_tests.py
"""

import os
import argparse
import json
import subprocess
import shlex
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def parse_args():
    """Parse arguments for the script."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config-file",
        action="store",
        default="locust_config.json",
        help="JSON file containing configs for tests",
    )

    parser.add_argument(
        "--output-folder",
        action="store",
        default="results",
        help="Folder to store outputs",
    )

    parser.add_argument(
        "--analyze-results-only",
        action="store_true",
        help="If this tag is included, analyze previously-run test output results only",
    )
    args = parser.parse_args()

    return args


def read_configs(config_file_path):
    """Read test configs from the file. The contents of each entry should follow the schema of a standard locust test config."""
    try:
        configs = json.load(open(config_file_path))
        return configs

    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot find file with name {config_file_path}")
    except json.decoder.JSONDecodeError:
        raise Exception("Cannot parse config file")


def run_single_test(
    host, locustfile, users, spawn_rate, run_time, output_folder, test_name
):
    """
    Runs a single locust test.

    This function takes locust parameters and runs a locust load test, saving the results to output_folder/test_name/.

    Args:
        host (str): host to test
        locustfile (str): locustfile to use
        users (int): number of users to simulate
        spawn_rate (int): number of users to spawn per second
        run_time (str): time to run the test for
        output_folder (str): The name of output folder
        test_name (str): The name of the test
    """

    # build html output path
    html_output = f"{output_folder}/html_reports/{test_name}_report.html"
    # make folder to store raw results
    os.makedirs(f"{output_folder}/raw/{test_name}", exist_ok=True)
    output_filepath = f"{output_folder}/raw/{test_name}/test"

    # run locust test
    locust_command = shlex.split(
        # The webUI should be enabled so that graphs are generated for the html reports. Hence not using --headless.
        f"locust --autostart --autoquit 2 --host {host} --locustfile {locustfile} -u {users} -r {spawn_rate} -t {run_time} --csv {output_filepath} --html {html_output}"
    )
    subprocess.run(locust_command)


def run_tests(config, output_folder):
    """
    This function takes a list of test configs and runs them using locust.

    Args:
        config (dict): dict of test config parameters
        output_folder (str): The name of output folder that results should be saved to
    """

    ### extract config params
    host = config.get("host")
    users_list = config.get("users_list")
    # Note: default spawn rate = no. of users up to max 100 users/sec.
    default_spawn_rate_list = [min(users, 100) for users in users_list]
    spawn_rate_list = config.get("spawn_rate_list", default_spawn_rate_list)
    run_time_list = config.get("run_time_list")
    locustfile_list = config.get("locustfile_list")

    ### create overall results folder to store results
    os.makedirs(output_folder, exist_ok=True)
    # create folder to store html reports
    os.makedirs(output_folder + "/html_reports", exist_ok=True)

    ### Run tests, looping through given config options
    # loop through locustfile used
    for locustfile in locustfile_list:
        # loop through number of users and run time
        for users_iter, users in enumerate(users_list):

            # get corresponding runtime
            run_time = run_time_list[users_iter]
            # get corresponding spawn rate
            spawn_rate = spawn_rate_list[users_iter]

            # name output files based on config params
            locustfile_no_ext = locustfile[:-3]
            test_name = f"{users}_user_{locustfile_no_ext}"

            print(
                f"""
                Running load test...
                Max users: {users}
                Spawn rate: {spawn_rate}
                Locustfile: {locustfile}
                Runtime: {run_time}
                """
            )

            # Run test (also saves results to file)
            run_single_test(
                host=host,
                locustfile=locustfile,
                users=users,
                spawn_rate=spawn_rate,
                run_time=run_time,
                output_folder=output_folder,
                test_name=test_name,
            )

            print(f"Finished {test_name} load test.")

    print(f"All tests complete. Results saved to {output_folder}.")


def collate_and_plot_results_per_test(config, output_folder):
    """
    This function loads results from previously-run tests and collates and plots them.

    Saves the following to file:
    - all_tests_response_times_vs_time.png: Grid of plots of response times for each test vs time elapsed
    - all_tests_reqs_per_sec_vs_time.png: Grid of plots of reqs/sec for each test vs time elapsed
    - all_tests_results.csv: CSV file containing the final locust stats for each test (results_df, also returned by function)

    Args:
        config (dict): dict of test config parameters
        output_folder (str): The name of output folder that results were saved to
    Returns:
        results_df (pd.DataFrame): dataframe containing the final locust stats for each test
    """

    ### Extract relevant config params
    users_list = config["users_list"]
    locustfile_list = config["locustfile_list"]

    ### Instantiate list to collect combined results
    result_df_list = []
    failures_df_list = []

    ### Prep figures for plots
    figsize_x = max(2.5 * len(users_list), 6)
    figsize_y = max(2.5 * len(locustfile_list), 6)
    # For response time plots
    f_rt, axes_rt = plt.subplots(
        len(locustfile_list),
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey="row",
        constrained_layout=True,
    )
    f_rt.supxlabel("Seconds Elapsed")
    # f_rt.supylabel("Response Time (ms)")

    # For requests/s + errors/s plots
    f_reqs, axes_reqs = plt.subplots(
        len(locustfile_list),
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey=True,
        constrained_layout=True,
    )
    f_reqs.supxlabel("Seconds Elapsed")
    # f_reqs.supylabel("Requests/s")

    # loop through locustfile used
    for locustfile_iter, locustfile in enumerate(locustfile_list):
        # loop through number of users
        for users_iter, users in enumerate(users_list):

            ### Collect saved results
            # Name of output files to load based on config params (same as in run_tests)
            locustfile_no_ext = locustfile[:-3]
            test_name = f"{users}_user_{locustfile_no_ext}"
            # Read test_stats_history.csv from results subfolder
            test_results = pd.read_csv(
                f"{output_folder}/raw/{test_name}/test_stats_history.csv"
            )
            # Create new "seconds_elapsed" column to use as x-axis for plots
            test_results["Seconds Elapsed"] = (
                test_results["Timestamp"] - test_results["Timestamp"][0]
            )

            ### Plot
            ## Response times
            # Median (50th percentile)
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="50%",
                label="Median (ms)",
                legend=None,
                ax=axes_rt[locustfile_iter, users_iter],
            )
            # 95th percentile
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="95%",
                label="95% (ms)",
                legend=None,
                ax=axes_rt[locustfile_iter, users_iter],
            )
            # remove axis labels for all subplots in but those in the bottom row and leftmost column
            axes_rt[locustfile_iter, users_iter].set_xlabel("")
            axes_rt[locustfile_iter, users_iter].set_ylabel("")
            if locustfile_iter == 0:
                axes_rt[locustfile_iter, users_iter].set_title(f"{users} users")
            if users_iter == 0:
                axes_rt[locustfile_iter, users_iter].set_ylabel(locustfile_no_ext)
            # add legend to top left plot only
            if locustfile_iter == 0 and users_iter == 0:
                axes_rt[locustfile_iter, users_iter].legend(loc="upper left")

            ## Reqs/s + Errors/s
            # Requests/s
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="Requests/s",
                label="Requests/s",
                legend=None,
                ax=axes_reqs[locustfile_iter, users_iter],
            )
            # Errors/s
            sns.lineplot(
                data=test_results,
                x="Seconds Elapsed",
                y="Failures/s",
                label="Failures/s",
                color="red",
                legend=None,
                ax=axes_reqs[locustfile_iter, users_iter],
            )
            # remove axis labels for all subplots in but those in the bottom row and leftmost column
            axes_reqs[locustfile_iter, users_iter].set_xlabel("")
            axes_reqs[locustfile_iter, users_iter].set_ylabel("")
            if locustfile_iter == 0:
                axes_reqs[locustfile_iter, users_iter].set_title(f"{users} users")
            if users_iter == 0:
                axes_reqs[locustfile_iter, users_iter].set_ylabel(locustfile_no_ext)
            # add legend to top left plot only
            if locustfile_iter == 0 and users_iter == 0:
                axes_reqs[locustfile_iter, users_iter].legend(loc="upper left")

            ### Collect final results into one table
            # Select last row of stats_history to get stats for the LAST 10 SECONDS OF THE TEST RUN.
            # Manually check the plots to make sure that the response times have flattened at this point.
            # if not, increase the run_time and rerun the load test.
            # To Do: Automate this. Requires a way to robustly determine when the response times have flattened.
            test_results_chosen = test_results.iloc[-1].copy()
            # add name of locustfile used to these results
            test_results_chosen.loc["locustfile"] = locustfile_no_ext
            # final row always has users = 0, so replace with actual number of users.
            test_results_chosen.loc["User Count"] = users
            # add results from this test to list
            result_df_list.append(test_results_chosen)

            ### Collect failures (if any) ###
            # Read failures.csv from results subfolder
            test_failures = pd.read_csv(
                f"{output_folder}/raw/{test_name}/test_failures.csv", header=0
            )
            if not test_failures.empty:
                # add name of locustfile and n users used to the failures df
                test_failures["locustfile"] = locustfile_no_ext
                test_failures["User Count"] = users
                # add failures from this test to list
                failures_df_list.append(test_failures)

    ### combine results into one dataframe
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

    # Make new output subfolder for processed results
    os.makedirs(output_folder + "/processed", exist_ok=True)

    # Save results and plots
    print("Saving all_tests_results.csv...")
    results_df.to_csv(f"{output_folder}/processed/all_tests_results.csv", index=False)
    
    if len(failures_df_list) > 0:
        # combine failures into one dataframe and save to file as well
        failures_df = pd.concat(failures_df_list, axis=0)
        failures_df = failures_df[['locustfile', 'User Count', 'Method', 'Name', 'Error', 'Occurrences']]
        failures_df.to_csv(f"{output_folder}/processed/all_tests_failures.csv", index=False)

    print("Saving visualizations for all tests...")
    f_rt.savefig(f"{output_folder}/processed/all_tests_response_times_vs_time.png")
    f_reqs.savefig(f"{output_folder}/processed/all_tests_reqs_per_sec_vs_time.png")

    return results_df


def plot_final_results_per_locustfile(results_df, output_folder):
    """
    Plots final results for each locustfile used. Saves the following to file:
    - locustfile_response_times_vs_users.png: Response times vs. number of users per locustfile
    - locustfile_reqs_per_sec_vs_users.png: Requests/s vs. number of users per locustfile
    """

    ### Create plots
    f, axes = plt.subplots(2, 1, figsize=(7, 7), constrained_layout=True)
    # line plot of median response time per request coloured by locustfile
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
        f"{output_folder}/processed/locustfile_response_times_vs_users.png", dpi=300
    )

    f, axes = plt.subplots(2, 1, figsize=(7, 7), constrained_layout=True)
    # line plot of max reqs/s coloured by locustfile
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
        f"{output_folder}/processed/locustfile_reqs_per_sec_vs_users.png", dpi=300
    )


def calculate_stats_per_locustfile(results_df, output_folder):
    """
    Calculates and saves the following to file:
    - final_summary_results.csv: CSV of final combined results for each locustfile (i.e. experiment)
    """

    # Initial response time per request (mean, median)
    # Max requests that can be handled per second by the server
    final_results = results_df.groupby("locustfile").agg(
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

    final_results.rename(
        columns={
            "Requests/s": "Max Requests/s",
            "Total Median Response Time": "Minimum Median Response Time",
            "Total Average Response Time": "Minimum Average Response Time",
        },
        inplace=True,
    )

    print("Saving final_summary_results.csv...")
    final_results.to_csv(
        f"{output_folder}/processed/final_summary_results.csv", index=True
    )


def main():
    """Run main script function."""
    args = parse_args()
    configs = read_configs(args.config_file)

    # Run the tests for each experiment (primary key) given in the config file
    for key in configs.keys():

        print(
            f"""
            #################################################
            ### Running experiment {key} ###
            #################################################
            """
        )
        config = configs[key]
        output_folder = f"{args.output_folder}/{key}"

        # if analyze-results-only arg is passed, skip running locust
        if args.analyze_results_only:
            pass
        else:
            run_tests(config=config, output_folder=output_folder)

        # analyze and save results to file
        results_df = collate_and_plot_results_per_test(
            config=config, output_folder=output_folder
        )
        calculate_stats_per_locustfile(
            results_df=results_df, output_folder=output_folder
        )
        if len(config["users_list"]) > 1:
            plot_final_results_per_locustfile(
                results_df=results_df, output_folder=output_folder
            )

    ## Redo for:
    # done - Messages from the validation dataset
    # done - Messages with typos
    # Short messages
    # Long messages


if __name__ == "__main__":
    main()
