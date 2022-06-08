June 6, 2022

CURRENT VERSION: aaq_core_template:v1.0.0
# API Instructions for AAQ Core App (Template)

Requests to all the endpoints below (except `/healthcheck`) must be authenticated with the bearer token in the header. This bearer token must be the same as the environment variable `INBOUND_CHECK_TOKEN`.

### Get top FAQs for an inbound message: `POST /inbound/check`

#### Params
|Param|Type|Description|
|---|---|---|
|`text_to_match`|required, string| The text to be matched|
|`metadata`|optional, can be list/dict/string/etc.|Any custom metadata (inbound phone number/hash, labels, etc.). This will be stored in the inbound query database.|
|`return_scoring`|optional, string, false by default|Setting this to "true" (lowercase) will return the match scores for each FAQ in the returned JSON.<br>*This will be large if there are many FAQs in the database, and hence should be used mainly for debugging. |

##### Example
```json
{
    "text_to_match": "is it normal to vomit every day for a week",
    "metadata": {
        "phone_number": "+12125551234",
        "joke": "what did the fish say"
    },
    "return_scoring": "true"
}
```

#### Response
|Param|Type|Description|
|---|---|---|
|`top_responses`|list[list[string]]|List of top matches, each match is a list [title, content].|
|`inbound_id`|integer|ID of inbound query, to be used when submitting feedback|
|`feedback_secret_key`|string|Secret key attached to inbound query, to be used when submitting feedback|
|`scoring`|dict|Scoring metadata, only returned if "return_scoring" == "true" in the request. Includes the spell-corrected query that we processed, under key spell_corrected|

##### Example
```json
{
  "top_responses": [
    ["FAQ #2 Title", "This is FAQ #2\"s content."],
    ["FAQ #1 Title", "This is FAQ #1\"s content."],
    ["FAQ #0 Title", "This is FAQ #0\"s content."]
  ],
  "inbound_id": 1234,
  "feedback_secret_key": "abcde12345",
  "scoring": {
    "787": {
      "faq_title": "FAQ #0 Title",
      "faq_content_to_send": "This is FAQ #0\"s content.",
      "tag_cs": {
        "rock": "0.16521704",
        "guitar": "0.22060609",
        "melody": "0.28887382",
        "chord": "0.1924967"
      },
      "overall_score": "0.19100773334503174"
    },
    "788": {
      "faq_title": "FAQ #1 Title",
      "faq_content_to_send": "This is FAQ #1\"s content.",
      "tag_cs": {
        "cheese": "0.2986467",
        "tomato": "0.188639",
        "bread": "0.37089044",
        "mustard": "0.14920337"
      },
      "overall_score": "0.20052412152290344"
    },
    // ... more FAQs
    "spell_corrected": "love going hiking What pack lunch"
  }
}
```

### Insert feedback for an inbound message: `PUT /inbound/feedback`
Use this endpoint to append feedback to an inbound message. You can continuously append feedback via this endpoint. All existing feedback will be saved.
#### Params
|Param|Type|Description|
|---|---|---|
|`inbound_id`|required, int|Provided in response to original /inbound/check POST.|
|`feedback_secret_key`|required, string|Provided in response to original /inbound/check POST.|
|`feedback`|optional, any format|Any custom feedback. Directly saved by us.|

#### Response
Response is one of the following pairs of (message, HTTP status)
  * `"Success", 200`: Successfully added feedback
  * `"No Matches", 404`: Did not match any previous inbound query
  * `"Incorrect Feedback Secret Key", 403`: Matched previous inbound query, but feedback secret key incorrect

### Check combinations of new tags: `POST /tools/check-new-tags`
The model will score each query message against each existing FAQ AND the new FAQ (defined by the tags in `tags_to_check`), and return the top N FAQs matched for each query.

This endpoint is used by the Admin app's "Check New FAQ Tags" tool.

This endpoint is disabled when `DEPLOYMENT_ENV=PRODUCTION`.


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
:warning: This endpoint is disabled when `DEPLOYMENT_ENV=PRODUCTION`.

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
