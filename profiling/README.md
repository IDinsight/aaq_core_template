# Code Profiling

Tests `inbound/check`, `feedback`, and `pagination` endpoints and saves results to file using `pytest` and `pyinstrument`.

# How to run

## Setup

1. Run `setup-dev`

2. Set secrets. Note: Set database secrets to the test database.

## Run the profilers

Run `make profile`

So that only the endpoints are profiled (and not the SQL injections etc), this command does the following:

1. Runs functions to clean and then populate the FAQ table with dummy FAQs.
2. Runs the profiler on the endpoints and saves results to file. By default this runs the "not extended" `pytest` - so only the google model.
3. Cleans the FAQ and inbounds databases.

Results will be saved in `profiling/output_folder/`
