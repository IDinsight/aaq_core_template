
# Load Testing

This is the readme for AAQ Load Testing.

## What is this?

This submodule extends the core functionality of the `locust` load-testing library to run multiple load-tests in succession and collect and save results to file.

# How to run

1. Install libraries in `requirements.txt`

2. Add the host addresses (unused hosts can be blank) and token to the conda environment variables. Note: It's assumed that the token is the same for all hosts.

    ```console
    STAGING_HOST=
    DEV_HOST=
    LOCAL_HOST=
    INBOUND_CHECK_TOKEN=
    ```

3. Create a `data/` folder in the repo root and place the CSV containing validation messages inside (e.g. for MomConnect, use `validation_khumo_labelled_aaq.csv`)

4. Set config parameters in `locust_config.json`. This file will be pre-filled but can be modified. See [config](#config-and-experiment-types) section below for details on how this file is formatted.

5. Run the main script.

    ```console
    python run_load_tests.py
    ```

    This script will loop through each experiment in the config file and its given test configurations and run each parameter combination through `locust`, saving results to file.

    > Note: Each experiment can specify multiple values for each parameter, and so multiple load-tests may be run for each experiment.

    The script can be run with the following command-line arguments:
    - `--config-file`: JSON file containing configs for tests.

        Default `locust_config.json`.

    - `--output-folder`: Folder to store outputs.

        Default `results`.

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
all_experiments_endoftest_results_summary.csv
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

3. `processed/`: Once all tests have concluded, the raw stats for all tests  are read, collated, plotted and saved here by the main script.

    > Note: End-of-test results are not reliable for ramped tests - see [ramped load-tests](#ramped-load-tests))

    Files created are described below:

    Presenting info for all tests

    ---

    Grid of response time and requests/sec progression plots for each test, similar to plots from the HTML report. Rows = locustfile used. Columns = number of users.

    ```console
    all_response_times_vs_time.png
    all_reqs_per_sec_vs_time.png
    ```

    End-of-test results for all tests:

    ```console
    endoftest_results_all.csv
    ```

    If there have been any failed requests, the following is also output which details the count and type of failures that occured:

    ```console
    failures_all.csv
    ```

    Presenting summarized results

    ---

    For each locustfile used (i.e. request type sent), present the minimum end-of-test response time and maximum reqs/sec achieved across all user counts:

    ```console
    endoftest_results_summary.csv
    ```

    Plots showing how end-of-test response times and reqs/sec differ for different user loads, disaggregated by locustfile used:

    ```console
    endoftest_response_times_vs_users.png
    endoftest_reqs_per_sec_vs_users.png
    ```

    > Note: These plots are not produced if multiple n_users were not tested.

### Example output folder structure

```console
📂results
┣ all_experiments_endoftest_results_summary.csv
┣ 📂dev_stepped_multi
┃ ┣ 📂html_reports
┃ ┃ ┣ 100_user_locustfile_same_msgs_report.html
┃ ┃ ┣ ...
┃ ┣ 📂processed
┃ ┃ ┣ all_reqs_per_sec_vs_time.png
┃ ┃ ┣ all_response_times_vs_time.png
┃ ┃ ┣ endoftest_reqs_per_sec_vs_users.png
┃ ┃ ┣ endoftest_response_times_vs_users.png
┃ ┃ ┣ endoftest_results_all.csv
┃ ┃ ┗ endoftest_results_summary.csv
┃ ┣ 📂raw
┃ ┃ ┣ 📂100_user_locustfile_same_msgs
┃ ┃ ┃ ┣ test_exceptions.csv
┃ ┃ ┃ ┣ test_failures.csv
┃ ┃ ┃ ┣ test_stats.csv
┃ ┃ ┃ ┗ test_stats_history.csv
┃ ┃ ┣ 📂100_user_locustfile_val_msgs
┃ ┃ ┗ ┗ ...
┃ ┣ 📂dev_single_ramped
┗ ┗ ┗ ...
```

# Config and experiment types

## Config file format

The config file used here is `.json` as opposed to locust's expected `.ini` style. This allows us to write defintions for multiple experiments without having to make a different config file for each, and is parsed automatically by the main script.

Each key-value pair here is a load-test experiment, where the key is the experiment name and the value is a dictionary of parameters expected by `locust`.

Each experiment entry reflects the core elements of a standard locust config file but with the key difference that parameters are given as lists as opposed to single values. This allows us to run multiple test configurations per experiment, namely to use different locustfiles (type of requests sent) and numbers of users.

## Experiment types

This submodule is designed to be able to run two types of experiments: constant and ramped load-tests. As many experiments can be added to the config file as necessary - the script will execute one after the other.

### *Constant load-tests*

Constant load-tests initiate the max number of users from the start and sustain the load for the given run-time.

When multiple request types (via different locustfiles) and numbers of users are specificed, the constant load-tests experiment outputs a grid of results that allows us to compare response times and requests/sec under stable load conditions.

An example of a config entry for multiple constant load-tests performed on the `STAGING_HOST` is given below:

```json
"simple_staging_stepped_multi": {
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

### *Ramped load-tests*

Ramped load-tests gradually increase number of users based on a given spawn-rate, up to a given max number of users, for a given run-time.

A ramped load-test is helpful in estimating the point at which a server starts to experience slowdowns and/or throw errors, but is more difficult to interpret. This difficulty is due to the delay between users spawning, their requests being responded to with different response times, and the rolling average that the stats are presented with.

Also note that end-of-test results are often unreliable or irrelevant in ramped load-tests (e.g. median and average response time values). A constant load-test is more suited to extracting stable response time results and can be repeated for any number of users as required.

An example of a config entry for a single ramped load-test is given below. This test is performed on the `STAGING_HOST`, with 2 users spawned per second, up to a maximum of 500 users, with a max run-time of 8 minutes.

```json
"simple_staging_ramping_single": {
    "host_label": "STAGING_HOST",
    "locustfile_list": [
        "locustfile_same_msgs.py",
        "locustfile_val_msgs.py"
    ],
    "users_list": [
        100
    ],
    "spawn_rate_list": [
        2
    ],
    "run_time_list": [
        "1m"
    ]
}
```

> Note that `spawn_rate_list` must be given here. If not given, spawn-rate will be set to number of users in the main script (up to a max 100 users/sec following Locust guidance). This default behaviour is as designed for constant load-tests.
