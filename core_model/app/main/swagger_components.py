from flask_restx import Api, fields, reqparse

from . import main

# Security
authorizations = {
    "Bearer": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": (
            "In the *'Value'* input box below, enter "
            "**'Bearer &lt;JWT&gt;'**, where JWT is the token"
        ),
    }
}
api = Api(
    main, title="AAQ Inbounds API", authorizations=authorizations, security="Bearer"
)

# Inbound fields
inbound_check_fields = api.model(
    "InboundCheckRequest",
    {
        "text_to_match": fields.String(
            description="The input message text to match",
            required=True,
            example="is it normal to crave anchovies for breakfast",
        ),
        "contexts": fields.List(
            fields.String,
            description=("List of message contexts. Each contect is a string "),
            required=False,
            example=["test", "deploy"],
        ),
        "metadata": fields.Raw(
            description=(
                "Can be list/dict/string/etc. Any custom metadata "
                "(inbound phone number/hash, labels, etc.). This will be "
                "stored in the inbound query database."
            ),
            required=False,
        ),
        "return_scoring": fields.Boolean(
            default=False,
            description=(
                "Setting this to 'true' (lowercase) will return "
                "the match scores for each FAQ in the returned JSON."
            ),
            required=False,
        ),
    },
)

# Outbound fields
scoring_vals = api.model(
    "faq_score",
    {
        "faq_title": fields.String,
        "faq_content_to_send": fields.String,
        "overall_score": fields.String(),
    },
)

wild_faq_id = fields.Wildcard(
    fields.Nested(scoring_vals),
    description=(
        "Scoring metadata for each FAQ, keyed by `faq_id`. "
        "This is only returned if 'return_scoring' == 'true' in the request. Includes "
        "the spell-corrected query that we processed, under key spell_corrected"
    ),
    example={
        "787": {
            "faq_title": "FAQ #0 Title",
            "faq_content_to_send": 'This is FAQ #0"s content.',
            "overall_score": "0.19100773334503174",
        },
        "788": {
            "faq_title": "FAQ #1 Title",
            "faq_content_to_send": 'This is FAQ #1"s content.',
            "overall_score": "0.20052412152290344",
        },
    },
)

response_dict = {
    "top_responses": fields.List(
        fields.List(
            fields.String,
        ),
        description=(
            "List of top matches, each match is a list "
            "`[faq_id, faq_title, faq_content]`."
        ),
        example=[
            ["789", "FAQ #2 Title", 'This is FAQ #2"s content.'],
            ["788", "FAQ #1 Title", 'This is FAQ #1"s content.'],
            ["787", "FAQ #0 Title", 'This is FAQ #0"s content.'],
        ],
    ),
    "inbound_id": fields.Integer(
        example=1234,
        description=(
            "ID of inbound query,"
            "to be used when submitting feedback or access other pages"
        ),
    ),
    "feedback_secret_key": fields.String(
        description=(
            "Secret key attached to inbound query, "
            "to be used when submitting feedback"
        ),
        example="feedback_secret_123",
    ),
    "inbound_secret_key": fields.String(example="inbound_secret_456"),
    "next_page_url": fields.Url(
        example="/inbound/92567/3?inbound_secret_key=inbound_secret_123",
        description="only returned when the next page exists",
    ),
    "scoring": wild_faq_id,
    "spell_corrected": fields.String(
        example="love going hiking What pack lunch",
        description=(
            "Spell corrected and preprocessed form of the "
            "inbound message. Useful for debugging."
        ),
    ),
}


response_check_fields = api.model("InboundCheckResponseModel", response_dict)

# Pagination inbound
# TODO: reqparse is deprecated, Switch to marshmallow or WegArgs
pagination_fields = {
    "prev_page_url": fields.Url(
        example="/inbound/92567/1?inbound_secret_key=inbound_secret_123",
        description="only returned when the previous page exists",
    ),
}
pagination_fields.update(response_dict)

pagination_response_fields = api.model("PaginationResponseModel", pagination_fields)
pagination_parser = reqparse.RequestParser()
pagination_parser.add_argument("inbound_secret_key", type=str, required=True)


# Feedback endpoint

feedback_json = {}
feedback_json["feedback_type"] = fields.String(
    required=True,
    example="positive",
    description="Should be either 'positive' or 'negative'",
)
feedback_json["faq_id"] = fields.Integer(
    required=False,
    example="12",
    description=(
        "Required if `feedback_type` is 'positive'. "
        "One of `page_number` or `faq_id` must be provided "
        "if `feedback_type` is 'negative'"
    ),
)
feedback_json["page_number"] = fields.Integer(
    required=False,
    example=2,
    description=(
        "One of `page_number` or `faq_id` must be provided "
        "if `feedback_type` is 'negative'"
    ),
)
feedback_request_dict = {
    "inbound_id": fields.Integer(
        required=True,
        description="Id of the inbound message this feedback is for",
        example="1234",
    ),
    "feedback_secret_key": fields.String(
        required=True,
        description="Secret key found in response to original inbound message",
        example="feedback-secret-123",
    ),
    "feedback": fields.Nested(api.model("FeedbackJSON", feedback_json)),
}

feedback_request_fields = api.model("FeedbackRequest", feedback_request_dict)
