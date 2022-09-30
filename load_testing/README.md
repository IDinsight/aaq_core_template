# Load Testing

This is the readme for AAQ Load Testing.

## What is this?

This submodule extends the core functionality of the `locust` load-testing library to run multiple load-tests in succession and collect and save results to file.

# How to run

1. Create a new python 3.9 environment

2. Install libraries in `requirements.txt`

3. Add the host addresses (unused hosts can be blank) and token as environment variables. If using conda, you may wish to add this to the [`env_var.sh`](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#macos-and-linux) file.
   Note: It's assumed that the token is the same for all hosts.

    ```console
    STAGING_HOST=
    DEV_HOST=
    LOCAL_HOST=
    INBOUND_CHECK_TOKEN=
    ```

4. Create a `data/` folder in the repo root and place the CSV containing validation messages inside (e.g. for MomConnect, use `validation_khumo_labelled_aaq.csv`)

5. Config file examples are provided in the `configs/` folder. Either alter parameters in pre-existing files or make your own.

    See [config](#config-and-experiment-types) section below for details on how this file is formatted.

6. Run the main script.

    ```console
    python main.py
    ```

    This script will loop through each experiment in the config file and its given test configurations and run each parameter combination through `locust`, saving results to file.

    > Note: Each experiment can specify multiple values for each parameter, and so multiple load-tests may be run for each experiment.

    The script can be run with the following command-line arguments:

    - `--config`: JSON file containing configs for tests.

        Default `configs/ramped_and_constant.json`.

        > Note: Use `full_suite.json` to run full test suite.

    - `--output`: Folder to store outputs.

        Default `output_folder`.

    - `--analyze-results-only`: If this tag is included, don't run any new tests and analyze previously-run test outputs only. Saved results must exactly correspond to the given config file.

# Results

## Live Monitoring

Results of tests can be monitored live through the Locust WebUI by going to the localhost address given in the terminal when tests are running.

## Saved to file

Results are saved to file at 4 stages:

1. During each test run
2. End of each test run
3. End of each experiment's set of test runs
4. End of all experiments

When all experiments are completed, a master summary CSV file is produced and placed directly into the root `output_folder/` called:

```console
combined_experiment_results.csv
```

> Note: End-of-test results are not reliable for ramped tests - see [ramped load-tests](#ramped-load-tests))

Results from each individual load-testing experiment are also saved under a corresponding `experiment_name/` subfolder. The following subfolders are then created inside:

1. `raw/`: While each test is running, raw stats and error info are flushed to disk every 10 seconds by Locust into a further subfolder titled `[users]_user_[locustfile]/`, corresponding to the test parameters. Files saved by Locust:

    ```console
    test_exceptions.csv
    test_failures.csv
    test_stats.csv
    test_stats_history.csv
    ```

2. `html_reports/`: At the end of each test, an HTML report made by Locust is saved here. Each report includes final stats and load-test progression plots.

3. `processed/`: Once all tests have concluded, the raw stats for all tests are read, collated, plotted and saved here by the main script.

    > Note: End-of-test results are not reliable for ramped tests - see [ramped load-tests](#ramped-load-tests))

    Files created are described below:

    Presenting info for all tests

    ***

    Grid of response time and requests/sec progression plots for each test, similar to plots from the HTML report. Rows = locustfile used. Columns = number of users.

    ```console
    per_test_response_time_vs_time.png
    per_test_reqs_sec_vs_time.png
    ```

    End-of-test results for all tests:

    ```console
    per_test_final_results.csv
    ```

    If there have been any failed requests, the following is also output which details the count and type of failures that occured:

    ```console
    per_test_failures.csv
    ```

    Presenting summarized results

    ***

    For each locustfile used (i.e. request type sent), present the minimum end-of-test response time and maximum reqs/sec achieved across all user counts:

    ```console
    experiment_results.csv
    ```

    Plots showing how end-of-test response times and reqs/sec differ for different user loads, disaggregated by locustfile used:

    ```console
    per_locustfile_response_times_vs_users.png
    per_locustfile_reqs_sec_vs_users.png
    ```

    > Note: These plots are not produced if multiple n_users were not tested.

### Example output folder structure

```console
📂output_folder
┣ all_experiments_endoftest_results_summary.csv
┣ 📂staging_constant_multi
┃ ┣ 📂html_reports
┃ ┃ ┣ 10_user_locustfile_same_msgs_report.html
┃ ┃ ┗ ...
┃ ┣ 📂processed
┃ ┃ ┣ experiment_results.csv
┃ ┃ ┣ per_locustfile_reqs_sec_vs_users.png
┃ ┃ ┣ per_locustfile_response_times_vs_users.png
┃ ┃ ┣ per_test_final_results.csv
┃ ┃ ┣ per_test_reqs_sec_vs_time.png
┃ ┃ ┗ per_test_response_time_vs_time.png
┃ ┣ 📂raw
┃ ┃ ┣ 10_user_locustfile_same_msgs_report
┃ ┃ ┃ ┣ test_exceptions.csv
┃ ┃ ┃ ┣ test_failures.csv
┃ ┃ ┃ ┣ test_stats.csv
┃ ┃ ┃ ┗ test_stats_history.csv
┃ ┃ ┣ 📂100_user_locustfile_val_msgs
┃ ┃ ┗ ┗ ...
┃ ┣ 📂staging_ramped
┗ ┗ ┗ ...
```

# Config and experiment types

## Config file format

The config file used here is `.json` as opposed to locust's expected `.ini` style. This allows us to write defintions for multiple experiments without having to make a different config file for each, and is parsed automatically by the main script.

Each key-value pair here is a load-test experiment, where the key is the experiment name and the value is a dictionary of parameters expected by `locust`.

Each experiment entry reflects the core elements of a [standard locust config file](https://docs.locust.io/en/stable/configuration.html) but with the key difference that parameters are given as lists as opposed to single values. This allows us to run multiple test configurations per experiment, namely to use different locustfiles (type of requests sent) and numbers of users.

## Experiment types

This submodule is designed to be able to run two types of experiments: constant and ramped load-tests. As many experiments can be added to the config file as necessary - the script will execute one after the other.

### _Constant load-tests_

Constant load-tests initiate the max number of users from the start and sustain the load for the given run-time.

When multiple request types (via different locustfiles) and numbers of users are specificed, the constant load-tests experiment outputs a grid of results that allows us to compare response times and requests/sec under stable load conditions.

An example of a config entry for multiple constant load-tests performed on the `STAGING_HOST` is given below:

```json
"staging_constant_multi": {
    "host_label": "STAGING_HOST",
    "locustfile_list": [
        "locustfile_same_msgs.py",
        "locustfile_val_msgs.py"
    ],
    "users_list": [
        1,
        10
    ],
    "run_time_list": [
        "30s",
        "30s"
    ]
}
```

> Note: Each entry in `run_time_list` must correspond to and will be used with its respective entry in `users_list`.

In this example, the main script will run locust load-tests for each locustfile and number of users combination.

### _Ramped load-tests_

Ramped load-tests gradually increase number of users based on a given spawn-rate, up to a given max number of users, for a given run-time.

A ramped load-test is helpful in estimating the point at which a server starts to experience slowdowns and/or throw errors, but is more difficult to interpret. This difficulty is due to the delay between users spawning, their requests being responded to with different response times, and the rolling average that the stats are presented with.

Also note that end-of-test results are often unreliable or irrelevant in ramped load-tests (e.g. median and average response time values). A constant load-test is more suited to extracting stable response time results and can be repeated for any number of users as required.

An example of a config entry for a single ramped load-test is given below. This test is performed on the `STAGING_HOST`, with 2 users spawned per second, up to a maximum of 500 users, with a max run-time of 8 minutes.

```json
"staging_ramped_50": {
    "host_label": "STAGING_HOST",
    "locustfile_list": [
        "locustfile_same_msgs.py",
        "locustfile_val_msgs.py"
    ],
    "users_list": [
        50
    ],
    "spawn_rate_list": [
        1
    ],
    "run_time_list": [
        "40s"
    ]
}
```

> Note that `spawn_rate_list` must be given here. If not given, spawn-rate will be set to number of users in the main script (up to a max 100 users/sec following Locust guidance). This default behaviour is as designed for constant load-tests.
