"""
This script loads a config file, runs multiple locust load tests, plots and writes results to file.
Functionality based on: github.com/mohsenSy/locust-tests-runner/blob/master/locust_run_tests.py
"""

import argparse
import json

from custom_load_testing.auto_load_testing import run_all_experiments


def parse_args():
    """Parses arguments for the script."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default="configs/ramped_and_constant.json",
        help="JSON file containing configs for tests",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        default="output_folder",
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
    """Read test configs from the file.

    Parameters
    ----------
    config_file : str

    Returns
    -------
    configs : dict
        Dictionary of test configs

    """
    configs = json.load(open(config_file))
    return configs


def main():
    """Run main script function."""
    args = parse_args()
    configs = read_configs(args.config)
    run_all_experiments(configs=configs, args=args)


if __name__ == "__main__":
    main()
