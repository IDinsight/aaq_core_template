# Code Profiling

Tests `inbound/check`, `feedback`, and `pagination` endpoints and saves results to file using `pytest` and `pyinstrument`.

See this [confluence page](https://idinsight.atlassian.net/wiki/spaces/PD/pages/2055798825/Code+Profiling+Tools) for details about the tools.

## How to run

### Setup

1. Run `setup-dev`

2. Set secrets. Note: Set database secrets to the test database.

3. Make a folder `profiling/data/` and place `faq_data.yaml` here (same data used in `validation/`)

### Run the profilers

Run `make profile`

So that only the endpoints are profiled (and not the SQL injections etc), this command does the following:

1. Runs functions to clean and then populate the FAQ table with 6 dummy FAQs.
2. Runs the profiler on the endpoints and saves results to file. By default this runs the "not extended" `pytest` - i.e. only the google model. Easiest way to change the model tested right now is to change the `conftest.py` config.
3. Cleans the FAQ and inbounds databases.

> Note: Since we only add 6 FAQs to the database, we set `top_n_responses=3` in `conftest.py` so that multiple pages of results are created and the `pagination` endpoint can be tested. This is the same as the other pytests in the repo.

Results will be saved in `profiling/output_folder/`

## TO-DO

- Add cPython profiling and options to Makefile target to allow for selection of profiler tool. Use [this](https://stackoverflow.com/a/2826068).
- Add easy functionality to test different models using an argument.
- Possibly: Separate endpoints so that each endpoint can be tested separately and a different HTML file is created per endpoint.
