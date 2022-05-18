December 9, 2021

CURRENT VERSION: praekelt_nlp_core:v1.0.0

# Initial setup

1. Save GoogleNews pretrained model binary, to be mounted into one of the containers. Download from https://www.dropbox.com/s/0ah0kslf7ac199g/GoogleNews-vectors-negative300-prenorm.bin?dl=0, and un-zip (so file is .bin).
- One way we do this for our other client is have the .bin in S3, so that whenever cluster instances are launched, they copy from S3 and then mount into the container.

2. Setup DB given attached instructions, creating two tables in the same database/schema.

# Images

The Docker image for the core model server is hosted on GHCR. Please contact IDinsight for the token (likely PAT) you need to access GHCR.

The image is:
- ghcr.io/idinsight/praekelt_nlp_core:v1.0.0
- Note that this image replaces praekelt_api_model (deprecated)

## Resources for images

The core model runs well on m5.xlarge (serving ~100 requests/second).

## Image setup

The inbound port mapping is 9902:9902 (TCP).

The GoogleNews pretrained binary (described above) must be mounted to (target inside the container): /usr/src/data/pretrained_wv_models/GoogleNews-vectors-negative300-prenorm.bin

The following environment variables are required:
- PG_ENDPOINT: Postgres instance endpoint
- PG_PORT: Postgres port
- PG_DATABASE: Database name
- PG_USERNAME
- PG_PASSWORD
- SENTRY_DSN
- SENTRY_ENVIRONMENT
- SENTRY_TRANSACTIONS_SAMPLE_RATE=1.0
- INBOUND_CHECK_TOKEN: Bearer token. Requests to /inbound/check and /auth-healthcheck must be authenticated with this bearer token in the header.
    - Can be anything you want, recommended alphanumeric.
- DEPLOYMENT_ENV
    - For production, this should be set to DEPLOYMENT_ENV=PRODUCTION, which disables the tag check and tag validation endpoints for stability.
    - Note that the other modules (`praekelt_nlp_demo` and `praekelt_nlp_dbui`) depend on `praekelt_nlp_core` endpoints that are disabled if DEPLOYMENT_ENV=PRODUCTION. Thus, the core model instance used by the other modules (i.e., that referenced by the environment variable MODEL_HOST in the other modules) should always be a non-production instance of the core model module. Specifically, even for (e.g.) the production praekelt_nlp_dbui instance, it should use a **non-production** instance of the core model module.

# API instructions

- Inbound check: `POST /inbound/check`
    - The following JSON keys are required in the POST:
        - text_to_match (required, string)
            - The text to be matched
        - metadata (optional; can be list/dict/string/etc.)
            - Any custom metadata (inbound phone number/hash, Praekelt labels, etc.). This will be stored in the inbound query database.
        - return_scoring (optional, string)
            - Value "true" (lowercase) will return scoring in the JSON returned
    - Example POST request:
        ```
        {
            "text_to_match": "what ingredients does the vaccine contain",
            "metadata": {
                "phone_number": "+12125551234",
                "joke": "what did the fish say"
            },
            "return_scoring": "true"
        }
        ```
    - The response will be JSON with the following keys:
        - top_responses (list of list of string)
            - List of top matches, each match is a list [title, content]
        - inbound_id (integer)
            - ID of inbound query, to be used when submitting feedback
        - feedback_secret_key (string)
            - Secret key attached to inbound query, to be used when submitting feedback
        - scoring (dict)
            - Scoring metadata, only returned if "return_scoring" == "true" in the request
            - Includes the spell-corrected query that we processed, under key spell_corrected

- Feedback: `PUT /inbound/feedback`
    - The following JSON keys are required in the PUT:
        - inbound_id (required, int)
            - Provided in response to original /inbound/check POST.
        - feedback_secret_key (required, string)
            - Provided in response to original /inbound/check POST.
        - feedback (optional, any format)
            - Any custom feedback. Directly saved by us.
    - You can continuously append feedback via this endpoint. All existing feedback will be saved.

- Check combinations of new tags: `POST /tools/check-new-tags`
    - The following JSON keys are required in the POST:
        - tags_to_check (required, list[str])
            - The list of possible tags, to check
        - queries_to_check (required, list[str])
            - A list of queries

    - The model will, for each query, score it against each existing FAQ plus the new FAQ (defined by the tags in tags_to_check), and return the top n FAQs matched for each query.

    - The response will be JSON with the following keys:
        - top_matches_for_each_query: list of lists of lists
            - In the outer list, each element corresponds to a query (in queries_to_check)
            - In the list that corresponds to each query: each element corresponds to a top FAQ matched by query
                - Each element is of format [Title of FAQ, score, list of tags]
                - The new FAQ with tags in tags_to_check is titled "*** New FAQ with these tags ***"
    - This endpoint is disabled when DEPLOYMENT_ENV=PRODUCTION.

- Authenticated healthcheck: `GET /auth-healthcheck`

- Refresh FAQs from database: `GET /internal/refresh-faqs`

- Find bad tags: `POST /tools/validate-tags`
    - The following JSON keys are required in the POST:
        - tags_to_check (required, list[str])
            - The list of possible tags, to check
    - The response will be a (possibly empty) JSON list of bad tags.
    - This endpoint is disabled when DEPLOYMENT_ENV=PRODUCTION.

- Requests to all of the endpoints above must be authenticated with bearer token in the header.

- Healthcheck: `GET /healthcheck`
    - No authentication.