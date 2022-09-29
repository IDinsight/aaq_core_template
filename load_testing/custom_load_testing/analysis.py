import logging
import os

import pandas as pd

from .plotting import (
    initialize_plot_grid,
    plot_results_vs_users,
    plot_test_stats_vs_time,
    plot_user_count,
)
from .processing import (
    calculate_per_experiment_results,
    combine_experiment_results,
    combine_final_test_results,
    get_test_result_folder_path,
    process_test_result,
)

logging.basicConfig(level=logging.INFO)


def analyse_test_results(experiment_configs, output_folder):
    """Loads, collates, saves, and plots results from previously-run tests.

    Files saved:
    - per_test_response_time_vs_time.png: Grid of plots of response times
    - per_test_reqs_sec_vs_time.png: Grid of plots of reqs/sec and errors/sec
    - per_test_final_results.csv: results_df CSV file containing the end-of-test locust stats for each test (also returned by function)
    - per_test_failures.csv: file containing failures for each test (only if there are any)

    Parameters
    ----------
    experiment_configs : dict
        dict of experiment parameters, where keys are parameter names and values are lists of parameter values
    output_folder : str
        Path to output folder

    Returns
    -------
    final_test_results : pd.DataFrame
        dataframe containing end-of-test results for each test

    """
    users_list = experiment_configs.get("users_list")
    locustfile_list = experiment_configs.get("locustfile_list")
    if experiment_configs.get("spawn_rate_list") is None:
        is_ramped = False
    else:
        is_ramped = True

    final_test_results_list = []
    test_failures_list = []

    f_rt, axes_rt = initialize_plot_grid(locustfile_list, users_list, is_ramped)
    f_reqs, axes_reqs = initialize_plot_grid(locustfile_list, users_list, is_ramped)

    # Loop through all tests and collate results
    for locustfile_id, locustfile in enumerate(locustfile_list):
        for users_id, users in enumerate(users_list):

            locustfile_no_ext = locustfile[:-3]  # remove .py extension
            test_results_folder = get_test_result_folder_path(
                locustfile_no_ext, users, output_folder
            )

            # Collect final result
            test_stats_history = pd.read_csv(
                test_results_folder + "test_stats_history.csv"
            )
            final_test_result = process_test_result(
                test_stats_history, locustfile, users
            )
            final_test_results_list.append(final_test_result)

            # Collect failures (if any)
            test_failures = pd.read_csv(
                test_results_folder + "test_failures.csv", header=0
            )
            if not test_failures.empty:
                test_failures["locustfile"] = locustfile_no_ext
                test_failures["User Count"] = users
                test_failures_list.append(test_failures)

            # Plot results
            # Median and 95th percentile response times
            ax_rt = axes_rt[locustfile_id, users_id]
            plot_test_stats_vs_time(
                test_stats_history=test_stats_history,
                ys=["50%", "95%"],
                labels=["Median (ms)", "95% (ms)"],
                ax=ax_rt,
                locustfile_id=locustfile_id,
                locustfile_no_ext=locustfile_no_ext,
                users_id=users_id,
                users=users,
            )
            # Requests and errors per second
            ax_reqs = axes_reqs[locustfile_id, users_id]
            plot_test_stats_vs_time(
                test_stats_history=test_stats_history,
                ys=["Requests/s", "Failures/s"],
                labels=["Requests/s", "Failures/s"],
                ax=ax_reqs,
                locustfile_id=locustfile_id,
                locustfile_no_ext=locustfile_no_ext,
                users_id=users_id,
                users=users,
            )

            # if test is ramped, plot user count vs time elapsed in bottom row
            if is_ramped and locustfile_id == len(locustfile_list) - 1:
                for axes in [axes_rt, axes_reqs]:
                    plot_user_count(
                        test_stats_history=test_stats_history,
                        ax=axes[-1, users_id],
                    )

    logging.info("Saving stats vs time plots for all tests...")
    os.makedirs(output_folder + "/processed", exist_ok=True)
    f_rt.savefig(f"{output_folder}/processed/per_test_response_time_vs_time.png")
    f_reqs.savefig(f"{output_folder}/processed/per_test_reqs_sec_vs_time.png")

    logging.info("Saving per_test_final_results.csv...")
    final_test_results = combine_final_test_results(final_test_results_list)
    final_test_results.to_csv(
        f"{output_folder}/processed/per_test_final_results.csv", index=False
    )

    if len(test_failures_list) > 0:
        logging.info("Saving per_test_failures.csv...")
        all_test_failures = pd.concat(test_failures_list, axis=0)
        all_test_failures = all_test_failures[
            [
                "locustfile",
                "User Count",
                "Method",
                "Name",
                "Error",
                "Occurrences",
            ]
        ]
        all_test_failures.to_csv(
            f"{output_folder}/processed/per_test_failures.csv",
            index=False,
        )
    else:
        logging.info(
            "No failures encountered during tests. Skipped saving per_test_failures.csv"
        )

    return final_test_results


def run_all_analysis(configs, args):
    """Runs analysis of experiment results and save plots and summaries to file.

    Parameters
    ----------
    configs : list of dicts
        List of dicts containing experiment configs
    args : dict
        Arguments from argparse

    """
    experiment_results_list = []
    for experiment_name, experiment_configs in configs.items():
        logging.info(
            f"""
            #
            # Running analysis for experiment {experiment_name}
            #
            """
        )

        experiment_output_folder = f"{args.output}/{experiment_name}"

        # analyse results per-test
        final_test_results = analyse_test_results(
            experiment_configs=experiment_configs,
            output_folder=experiment_output_folder,
        )

        if len(experiment_configs["users_list"]) > 1:
            plot_results_vs_users(
                final_test_results=final_test_results,
                output_folder=experiment_output_folder,
                y="Total Median Response Time",
                filename="per_locustfile_response_times_vs_users.png",
            )
            plot_results_vs_users(
                final_test_results=final_test_results,
                output_folder=experiment_output_folder,
                y="Requests/s",
                filename="per_locustfile_reqs_sec_vs_users.png",
            )

        logging.info(
            "Saving final results across all tests within an experiment: per_experiment_results.csv..."
        )
        experiment_results = calculate_per_experiment_results(
            final_test_results=final_test_results,
            experiment_name=experiment_name,
        )
        experiment_results.to_csv(
            f"{experiment_output_folder}/processed/per_experiment_results.csv",
            index=True,
        )
        experiment_results_list.append(experiment_results)

    logging.info(
        "Saving summary of results across all experiments: combined_experiment_results.csv..."
    )
    all_experiments_results = combine_experiment_results(
        experiment_results_list=experiment_results_list
    )
    all_experiments_results.to_csv(
        f"{args.output}/combined_experiment_results.csv",
        index=True,
    )
