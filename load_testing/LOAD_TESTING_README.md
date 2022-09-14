
# Load Testing

This is the readme for AAQ Load Testing.

## What is this?

This submodule extends the core functionality of the `locust` load testing library to run multiple load tests in succession and collect and save results to file.

## How to run

1. Install libraries in `requirements.txt`.

2. Add the relevant host addresses and token to app_secrets.py in repo. Note: It's assumed that the token is the same for all hosts.

    ```console
    STAGING_HOST=
    DEV_HOST=
    LOCAL_HOST=
    INBOUND_CHECK_TOKEN=
    ```

3. Create a `data/` folder in the repo root and place the CSV containing validation messages inside (For MomConnect, use `validation_khumo_labelled_aaq.csv`)

4. Set test config parameters in `locust_config.json`. This config will be pre-filled but can be modified. Note: See "Config and experiment types" section below for details on how this config file is formatted.

5. Run the main script. This script will loop through each config entry and its corresponding locustfiles and users lists, running each combination through `locust` and saving results to file.

    ```console
    python run_load_tests.py
    ```

    This script can be run with the following commandline arguments:
    - `--config-file`: JSON file containing configs for tests.

        Default `locust_config.json`.

    - `--output-folder`: Folder to store outputs.

        Default `results`.

    - `--analyze-results-only`: If this tag is included, analyze previously-run test output results only. Saved results must exactly correspond to the given config file.

## Results

---

### Live

Results of tests can be monitored live through the Locust WebUI by going to the localhost address given in the terminal when tests are running.

### Saved to file

Results are saved under the `output-folder/` folder and the corresponding `experiment_name/` subfolder for each experiment in the config file.

Results are saved at during each test run, at the end of each test run, and at conclusion of all test runs into the following subfolders:

1. `raw/`: While each test is running, raw stats and error info are flushed to disk every 10 seconds by Locust into a further subfolder titled `[users]_user_[locustfile]/`, corresponding to the parameters of the test. Files saved by locust:

    ```console
    test_exceptions.csv
    test_failures.csv
    test_stats.csv
    test_stats_history.csv
    ```

2. `html_reports/`: At the end of each test, HTML reports made by Locust are saved here. Each report includes final stats and load test progression plots.

3. `processed/`: Once all tests have concluded, the raw stats for all tests  are read, collated, plotted and saved here by the main script. Files created are described below.

    [Presenting info for all tests]

    Grid of progression plots for each test - similar to plots from the HTML report. Rows are locustfile used, columns are number of users:

    ```console
    all_tests_reqs_per_sec_vs_time.png
    all_tests_response_times_vs_time.png
    ```

    > Only the above files are output for ramped tests - see [ramped load-tests](#ramped-load-tests) section for details.

    End-of-test results for all tests:

    ```console
    all_tests_results.csv
    ```

    [Presenting summarized results]

    Minimum response time and maximum reqs/sec obtained across all user counts used for each locustfile (i.e. host and request-type combination):

    > This table is a summary of `all_tests_results.csv`.

    ```console
    final_summary_results.csv
    ```

    Plots comparing final response times and reqs/sec results:

    ```console
    locustfile_reqs_per_sec_vs_users.png
    locustfile_response_times_vs_users.png
    ```

Example output folder structure:

```console
📂results
┣ 📂dev_stepped_multi
┃ ┣ 📂html_reports
┃ ┃ ┣ 100_user_locustfile_same_msgs_report.html
┃ ┃ ┣ ...
┃ ┣ 📂processed
┃ ┃ ┣ all_tests_reqs_per_sec_vs_time.png
┃ ┃ ┣ all_tests_response_times_vs_time.png
┃ ┃ ┣ all_tests_results.csv
┃ ┃ ┣ final_summary_results.csv
┃ ┃ ┣ locustfile_reqs_per_sec_vs_users.png
┃ ┃ ┗ locustfile_response_times_vs_users.png
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

## Config and experiment types

---

The config file used here is `.json` as opposed to locust's expected `.ini` style. This allows us to write defintions for multiple experiments without having to make a different config file for each, and is parsed automatically by the main script. Each key-value pair here is a load-test experiment, where the key is the experiment name and the value is a dictionary of parameters required to run `locust`.

Each experiment entry reflects the core elements of a standard locust config file but with the key difference that parameters are given as lists so that we can run multiple tests configurations, namely to use different locustfiles (type of requests) and number of users.

This submodule is designed to be able to run two types of experiments. As many experiments can be added to the config file as necessary - the script will execute one after the other.

### Constant load-tests

Constant load-tests initiate the max number of users from the start and sustain the load for a given run-time.

When different numbers of users and request types are specificed (i.e. different locustfiles), the constant load-tests experiment produces a grid of results that allows us to compare across stable load conditions.

Example of config for multiple constant load-tests performed on the `STAGING_HOST`:

```json
"experiment_name":{
    "host": "STAGING_HOST",
    "locustfile_list": [
        "locustfile_same_msgs.py",
        "locustfile_val_msgs.py",
    ],
    "users_list": [
        1,
        10,
    ],
    "run_time_list": [
        "30s",
        "30s",
    ]
}
```

> Note: Each entry in `run_time_list` must correspond to and will be used with its respective entry in `users_list`.

In this example, the main script will run locust load-tests for each locustfile and n_users combination.

### Ramped load-tests

Ramped load-tests gradually increase number of users based on the spawn-rate up to the max number of users, for a given run-time.

The ramped load-test is helpful in pinpointing roughly at which point the server starts to misbehave/experience slowdowns, but is more difficult to interpret given the delay between users spawning, their requests being responded to with different response times, and the rolling average that the stats are presented with.

Example of config entry for a single ramped load-test performed on the `STAGING_HOST` with 2 users spawned per second up to 500 a maximum of 500 users. Max run-time is capped at 8 minutes.

```json
"staging_ramping_single": {
    "host": "STAGING_HOST",
    "locustfile_list": [
        "locustfile_same_msgs.py",
        "locustfile_val_msgs.py",
    ],
    "users_list": [
        500
    ],
    "spawn_rate_list": [
        2
    ],
    "run_time_list": [
        "8m"
    ]
    },
```

> Note that `spawn_rate_list` must be given here. If not given, spawn-rate will be set to number of users in the main script (same as constant load-tests).

#### Note re. ramped experiment outputs

For ramped tests, only the **progression plots** for each test are saved to file.

This is because the end-of-test results are often not reliable or relevant in non-stable tests (e.g. median and average response time values). The constant load-test experiment type above is more suited to extracting stable response time results and can be repeated for any number of users if required.
