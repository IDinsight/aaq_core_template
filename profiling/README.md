# Code Profiling

Tests `inbound/check`, `feedback`, and `pagination` endpoints and saves results to file using `pytest` and `pyinstrument`.

See this [confluence page](https://idinsight.atlassian.net/wiki/spaces/PD/pages/2055798825/Code+Profiling+Tools) for details about the tools.

# How to run

## Setup

1. Run `make setup-dev`

2. Install `faqt` through `pip install git+https://@github.com/IDinsight/faqt.git@v0.1.0`

3. Set the following secrets as environment variables (e.g. using `env_vars.sh` for `conda`)

    ```console
    INBOUND_CHECK_TOKEN=
    PG_ENDPOINT=
    PG_PASSWORD=
    TOKEN_MACHINE_USER=
    PROMETHEUS_MULTIPROC_DIR=
    ```

4. Decide whether you want to test real FAQs in the Dev DB or want to use dummy test FAQs through Test DB.

## Dev DB - use real FAQs

1. In `profiling/configs/base.yaml`, set the following to the dev database:

    ```console
    PG_USERNAME=
    PG_DATABASE=
    ```

2. Run either of the following commands:

    - `make profile-dev-google` to produce report for just the google model
    - `make profile-dev-fasttext` to produce report for just the custom embeddings model

## Test DB - Add and use dummy FAQs

1. In `profiling/configs/base.yaml`, set the following to the test database:

    ```console
    PG_USERNAME=
    PG_DATABASE=
    ```

2. Symlink `tests/data/faq_data.yaml` to `profiling/data/faq_data.yaml` using:

    ```console
    ln -s $(pwd)/tests/data/faq_data.yaml profiling/data
    ```

3. Run either of the following commands:

- `make profile-test-google` to produce report for just the google model
- `make profile-test-fasttext` to produce report for just the custom embeddings model

So that only the endpoints are profiled (and not the SQL injections etc), this command does the following:

1. Runs functions to clean and then populate the FAQ table with 6 dummy FAQs.
2. Runs the profiler on the endpoints and saves results to file. By default this runs the "not extended" `pytest` - i.e. only the google model. Easiest way to change the model tested right now is to change the `conftest.py` config.
3. Cleans the FAQ and inbounds databases.

> Note: Since we only add 6 FAQs to the database, we set `top_n_responses=3` in `conftest.py` so that multiple pages of results are created and the `pagination` endpoint can be tested. This is the same as the other pytests in the repo.

Results will be saved in `profiling/outputs/`

## TO-DO

- Add cPython profiling and options to Makefile target to allow for selection of profiler tool. Use [this](https://stackoverflow.com/a/2826068).
- Possibly: Separate endpoints so that each endpoint can be tested separately and a different HTML file is created per endpoint.
