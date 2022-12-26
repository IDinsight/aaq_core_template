Oct 19, 2022

CURRENT VERSION: aaq_core_template:v1.1.0
# API Instructions for AAQ Core App (Template)

Requests to all the endpoints below (except `/healthcheck`) must be authenticated with the bearer token in the header. This bearer token must be the same as the environment variable `INBOUND_CHECK_TOKEN`.

### Get top FAQs for an inbound message: `POST /inbound/check`

See `<MODEL_HOST>:9902/` for API details.

### Get paginated responses: `GET /inbound/<inbound_id>/<page_id>`

See `<MODEL_HOST>:9902/` for API details.

### Insert feedback for an inbound message: `PUT /inbound/feedback`
Use this endpoint to append feedback to an inbound message. You can continuously append feedback via this endpoint. All existing feedback will be saved.

Test the endpoint at `<MODEL_HOST>:9902/`.

#### Params
|Param|Type|Description|
|---|---|---|
|`inbound_id`|required, int|Provided in response to original /inbound/check POST.|
|`feedback_secret_key`|required, string|Provided in response to original /inbound/check POST.|
|`feedback`|json|See the examples for recommended formats. Directly saved by us.|

##### Example
The following only shows required fields. Any other key/values sent are not parsed or checked and simply saved to the DB.

For positive feedback (i.e. user says the chosen content answered their question),
```json
{"feedback_secret_key": "b06041c9b454822",
 "inbound_id": "101",
 "feedback": {
    "feedback_type": "positive",
    "faq_id": "12"
    // ...
  }
 }
```

For negative feedback on a specific FAQ content,
```json
{"feedback_secret_key": "b06041c9b454822",
 "inbound_id": "101",
 "feedback": {
    "feedback_type": "negative",
    "faq_id": "12"
    // ...
  }
 }
```

For negative feedback on the entire page of FAQs,
```json
{"feedback_secret_key": "b06041c9b454822",
 "inbound_id": "101",
 "feedback": {
    "feedback_type": "negative",
    "page_number": "2"
    // ...
  }
 }
```

#### Response
Response is one of the following pairs of (message, HTTP status)
  * `"Success", 200`: Successfully added feedback
  * `"No Matches", 404`: Did not match any previous inbound query by `inbound_id`
  * `"Incorrect Feedback Secret Key", 403`: Matched previous inbound query by `inbound_id`, but `feedback_secret_key` is incorrect

### Check combinations of new tags: `POST /tools/check-new-tags`
⚠️ This endpoint is disabled when `DEPLOYMENT_ENV=PRODUCTION`.

The model will score each query message against each existing FAQ AND the new FAQ (defined by the tags in `tags_to_check`), and return the top N FAQs matched for each query.

This endpoint is used by the Admin app's "Check New FAQ Tags" tool.


#### Params
|Param|Type|Description|
|---|---|---|
|`tags_to_check`|required, list[string]|The list of possible tags for a new FAQ|
|`queries_to_check`|required, list[string]|A list of text messages to match|

#### Response
|Param|Type|Description|
|---|---|---|
|`top_matches_for_each_query`|list[list[list]]|In the outer list, each element corresponds to a query message (in `queries_to_check`)<br>In the list that corresponds to each query: each element corresponds to a top FAQ matched by query. Each element is of format [Title of FAQ, score, list of tags]. The new FAQ with tags in `tags_to_check` is titled "*** New FAQ with these tags ***"|

### Find bad tags: `POST /tools/validate-tags`
⚠️ This endpoint is disabled when `DEPLOYMENT_ENV=PRODUCTION`.

#### Params
|Param|Type|Description|
|---|---|---|
|`tags_to_check`|required, list[string]|The list of tags to validate|

#### Response
The response will be a (possibly empty) JSON list of bad tags.


### Refresh FAQs from database: `GET /internal/refresh-faqs`
Hitting this endpoint will re-load FAQs from the database table `faqmatches`.

### Healthcheck: `GET /healthcheck`
Checks for connection to DB, whether FAQs can be refreshed from DB, whether FAQs and word embedding model are loaded correctly, and that the target table `inbounds` exists.

No authentication is required for this endpoint.

### Authenticated healthcheck: `GET /auth-healthcheck`
Same as `GET /healthcheck` but requires authentication.


### Prometheus metrics: `GET /metrics`
If you are using Prometheus, the metrics can be scraped from this endpoint.
