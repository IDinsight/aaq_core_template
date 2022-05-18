"""
# MODEL TOOLS ENDPOINTS
"""
import os
from functools import wraps

from faqt.model.embeddings import model_search_word
from flask import abort, current_app, jsonify, request

from ..data_models import TemporaryModel
from ..prometheus_metrics import metrics
from . import main
from .auth import auth


def active_only_non_prod(func):
    """
    Decorator ensures route is only active in a non-prod environment
    """

    @wraps(func)
    def route(*args, **kwargs):
        """
        Abort route if env is PRODUCTION
        """
        if os.getenv("DEPLOYMENT_ENV") == "PRODUCTION":
            return abort(404)
        else:
            return func(*args, **kwargs)

    return route


@main.route("/tools/check-new-tags", methods=["POST"])
@metrics.do_not_track()
@auth.login_required
@active_only_non_prod
def check_new_tags():
    """
    Handles requests to check possible tags for a new FAQ. Accepts list of
    tags and list of queries, and returns top FAQ matches for each query,
    sourcing from existing FAQs + new FAQ defined by tags.

    Parameters
    ----------
    request (request proxy; see https://flask.palletsprojects.com/en/1.1.x/reqcontext/)
        The request should be sent as JSON with fields:
        - tags_to_check (required, list[str])
        - queries_to_check (required, list[str])

    Returns
    -------
    JSON
        Fields:
        - top_matches_for_each_query: list of lists of lists
            - Outer list: each element corresponds to a query (in queries_to_check)
                - Inner list: each element corresponds to a top FAQ matched by query
                    - E.g., [Title of FAQ, score, list of tags]
            - New FAQ is titled "*** NEW TAGS MATCHED ***"
    """
    req_json = request.json
    temp_faq = TemporaryModel(
        faq_id="TEMP",
        faq_title="*** NEW TAGS MATCHED ***",
        faq_tags=req_json["tags_to_check"],
        faq_content_to_send="",
    )
    original_faqs = current_app.faqs
    with_temp_faqs = original_faqs + [temp_faq]

    current_app.faqt_model.set_tags(with_temp_faqs)

    json_return = {}
    json_return["top_matches_for_each_query"] = []

    for query_to_check in req_json["queries_to_check"]:
        processed_message = current_app.text_preprocessor(query_to_check)
        matches, scoring, _ = current_app.faqt_model.score(processed_message)

        matched_faq_titles = set()
        top_matches = []

        for id in sorted(
            scoring, key=lambda x: scoring[x]["overall_score"], reverse=True
        ):
            if scoring[id]["faq_title"] not in matched_faq_titles:
                top_matches.append(
                    [
                        scoring[id]["faq_title"],
                        "%0.4f" % scoring[id]["overall_score"],
                        list(scoring[id]["tag_cs"].keys()),
                    ]
                )
                matched_faq_titles.add(scoring[id]["faq_title"])

            if len(matched_faq_titles) == current_app.faqt_model.n_top_matches:
                break

        json_return["top_matches_for_each_query"].append(top_matches)

    current_app.faqt_model.set_tags(original_faqs)

    # Flask automatically calls jsonify
    return json_return


@main.route("/tools/validate-tags", methods=["POST"])
@metrics.do_not_track()
@auth.login_required
@active_only_non_prod
def validate_tags():
    """
    Validates tags. Returns list of invalid tags (may be empty list)

    Parameters
    ----------
    request (request proxy; see https://flask.palletsprojects.com/en/1.1.x/reqcontext/)
        The request should be sent as JSON with fields:
        - tags_to_check (required, list[str])

    Returns
    -------
    JSON
        List of invalid tags (may be empty)
    """

    req_json = request.json
    failed_tags = []

    for tag in req_json["tags_to_check"]:
        if (
            model_search_word(
                tag,
                current_app.faqt_model.w2v_model,
                current_app.faqt_model.glossary,
            )
            is None
        ):
            failed_tags.append(tag)

    return jsonify(failed_tags)
