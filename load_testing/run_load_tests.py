"""
This script loads a config file, runs multiple locust load tests, plots and writes results to file.
Functionality based on: github.com/mohsenSy/locust-tests-runner/blob/master/locust_run_tests.py
"""

### Import libraries
import argparse
import json

### Import custom functions
import functions_auto_load_testing


def parse_args():
    """Parses arguments for the script."""

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


def read_configs(config_file):
    """
    Read test configs from the file.

    Args:
        config_file (str): JSON file containing configs for tests
    Returns:
        configs (dict): Dictionary of test configs
    """

    try:
        configs = json.load(open(config_file))
        return configs

    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot find file with name {config_file}")
    except json.decoder.JSONDecodeError:
        raise Exception("Cannot parse config file")


def main():
    """Run main script function."""
    args = parse_args()
    configs = read_configs(args.config_file)
    functions_auto_load_testing.run_all_experiments(configs=configs, args=args)

if __name__ == "__main__":
    main()
