##############################################################################
# INBOUND ENDPOINTS
##############################################################################
import os
from base64 import b64encode
from collections import defaultdict
from datetime import datetime
from math import ceil

import numpy as np
from flask import current_app, request, url_for
from flask_restx import Resource
from sqlalchemy.orm.attributes import flag_modified

from ..data_models import Inbound
from ..database_sqlalchemy import db
from ..prometheus_metrics import metrics
from .auth import auth
from .swagger_components import (
    api,
    feedback_request_fields,
    inbound_check_fields,
    pagination_parser,
    pagination_response_fields,
    response_check_fields,
)


@api.route("/inbound/check")
class InboundCheck(Resource):
    """
    Handles inbound queries, matching messages to FAQs in database.

    Note: `scoring_output` and `json_return` and saving the Inbound to Db are very
    tightly coupled. It needs a significant change in what is saved and returned in
    order to decouple them. Parking it for now in order to not introduce
    breaking changes.

    Parameters
    ----------
    request (request proxy; see https://flask.palletsprojects.com/en/1.1.x/reqcontext/)
        The request should be sent as JSON with fields:
        - text_to_match (required, string)
        -context (optional,List[string])
        - metadata (optional, list/string/dict/etc.)
            - Any custom metadata
        - return_scoring (optional, string)
            - "true" will return scoring in returned JSON

    Returns
    -------
    JSON
        Fields:
        - top_responses: list of top matches, each match is a list [title, content]
        - inbound_id: id of inbound query, to be used when submitting feedback
        - feedback_secret_key: secret key attached to inbound query, to be used when
          submitting feedback
        - inbound_secret_key: Secret key attached to inbound query, to be used for
          requesting paginated results
        - scoring: scoring dictionary, only returned if "return_scoring" == "true";
          further described in return_faq_matches
        - spell_corrected: Spell corrected and preprocessed form of the
        inbound message. Useful for debugging.
        - next_page_url: only if the next page exists, the path to request
        next page of results.
    """

    @api.doc(model=response_check_fields, body=inbound_check_fields, security="Bearer")
    @metrics.do_not_track()
    @metrics.summary(
        "inbound_by_status_current",
        "Inbound latencies current",
        labels={"status": lambda r: r.status_code},
    )
    @metrics.counter(
        "inbound_by_status",
        "Inbound invocations counter",
        labels={"status": lambda r: r.status_code},
    )
    @auth.login_required
    def post(self):
        """
        See class docstring for details.
        """
        incoming = request.json
        if "return_scoring" in incoming:
            return_scoring = incoming["return_scoring"]
            return_scoring = (return_scoring is True) or (return_scoring == "true")
        else:
            return_scoring = False

        if (
            "context" in incoming
            and len(incoming["context"]) > 0
            and current_app.is_context_active
        ):
            contexts = incoming["context"]
            weights_dic = current_app.contextualizer.get_context_weights(contexts)
            weights = list(weights_dic.values())
        else:
            weights = None

        result = current_app.faqt_model.score_contents(
            incoming["text_to_match"],
            return_spell_corrected=True,
            return_tag_scores=True,
            weights=weights,
        )

        word_vector_scores = result["overall_scores"]
        spell_corrected = result["spell_corrected"]
        tag_scores = []  # result["tag_scores"]

        max_pages = ceil(
            len(word_vector_scores) / current_app.config["N_TOP_MATCHES_PER_PAGE"]
        )

        secret_keys = generate_secret_keys()
        scoring_output = prepare_scoring_as_json(
            current_app.faqs, word_vector_scores, tag_scores
        )
        json_return = prepare_return_json(
            scoring_output, secret_keys, return_scoring, 1
        )
        scoring_output["spell_corrected"] = " ".join(spell_corrected)
        inbound_id = save_inbound_to_db(
            incoming, scoring_output, json_return, secret_keys
        )
        json_return = finalise_return_json(json_return, inbound_id, 1, max_pages)

        return json_return


@api.route("/inbound/<int:inbound_id>/<int:page_number>")
class InboundResultsPage(Resource):
    """
    Handles getting different pages for requests that have already been processed.
    Parameters
    ----------
    inbound_id: Int
        The id of an existing inbound
    page_number; Int
        The page number to return
    Returns
    -------
    JSON
        Fields:
        - top_responses: list of matches belonging to this page, each match
        is a list [title, content]
        - inbound_id: id of inbound query, to be used when submitting feedback
        - feedback_secret_key: secret key attached to inbound query, to be used when
          submitting feedback
        - inbound_secret_key: Secret key attached to inbound query, to be used for
          requesting paginated results
        - scoring: scoring dictionary, only returned if "return_scoring" == "true";
          further described in return_faq_matches
        - next_page_url: only if the next page exists, the path to request
        next page of results.
        - prev_page_url: only if the previous page exists, the path to request
        previous page of results.
    """

    @api.doc(security="Bearer", model=pagination_response_fields)
    @api.expect(pagination_parser)
    @metrics.do_not_track()
    @metrics.summary(
        "pagination_latencies_by_status",
        "Pagination latencies",
        labels={"status": lambda r: r.status_code},
    )
    @metrics.counter(
        "pagination_by_page_number",
        "Number of requests by page number",
        labels={"page_number": lambda: request.view_args["page_number"]},
    )
    @auth.login_required
    def get(self, inbound_id, page_number):
        """
        See class docstring for details.
        """
        # check inbound key
        orig_inbound = Inbound.query.filter_by(inbound_id=inbound_id).first()
        secret_key = request.args["inbound_secret_key"]
        page_number = int(page_number)

        if orig_inbound is None:
            return f"No inbound message with `id` {inbound_id} found", 404
        elif orig_inbound.inbound_secret_key != secret_key:
            return "Incorrect Inbound Secret Key", 403

        scoring_output = orig_inbound.model_scoring
        _ = scoring_output.pop("spell_corrected")
        max_pages = ceil(
            len(scoring_output) / current_app.config["N_TOP_MATCHES_PER_PAGE"]
        )

        if (page_number > max_pages) or (page_number < 1):
            return (
                (
                    "Page does not exist. Min pages number is 1. Max page number for "
                    f"`id` {inbound_id} is {max_pages}."
                ),
                404,
            )

        keys = {
            "feedback_secret_key": orig_inbound.feedback_secret_key,
            "inbound_secret_key": orig_inbound.inbound_secret_key,
        }

        json_return = prepare_return_json(scoring_output, keys, False, page_number)
        json_return = finalise_return_json(
            json_return, inbound_id, page_number, max_pages
        )

        return json_return


@api.route("/inbound/feedback")
class InboundFeedback(Resource):
    """
    Handles inbound feedback

    Parameters
    ----------
    request (request proxy; see https://flask.palletsprojects.com/en/1.1.x/reqcontext/)
        The request should be sent as JSON with fields:
        - "inbound_id" (required, used to match original inbound query)
        - "feedback_secret_key" (required, used to match original inbound query)
        - "feedback"

    Returns
    -------
    str, HTTP status
        Successful: "Success", 200
        Did not match any previous inbound query: "No Matches", 404
        Matched previous inbound query, but feedback secret key incorrect:
            "Incorrect Feedback Secret Key", 403
    """

    @api.doc(body=feedback_request_fields)
    @metrics.do_not_track()
    @metrics.summary(
        "feedback_by_status_current",
        "Feedback requests latencies current",
        labels={"status": lambda r: r.status_code},
    )
    @metrics.counter(
        "feedback_by_status",
        "Feedback invocations counter",
        labels={"status": lambda r: r.status_code},
    )
    @auth.login_required
    def put(self):
        """
        See class docstring for details.
        """
        feedback_request = request.json
        orig_inbound = Inbound.query.filter_by(
            inbound_id=feedback_request["inbound_id"]
        ).first()

        if orig_inbound is None:
            return "No Matches", 404
        elif (
            orig_inbound.feedback_secret_key != feedback_request["feedback_secret_key"]
        ):
            return "Incorrect Feedback Secret Key", 403
        elif bad_feedback_schema(feedback_request["feedback"]):
            return "Malformed Feedback JSON", 400

        if orig_inbound.returned_feedback:
            # BACKWARDS COMPATIBILITY
            # Previously, instead of maintaining orig_inbound.returned_feedback as a
            # list, we saved a dict. So we convert dict to [dict], so that we can append
            # without overwriting the original feedback.
            if not isinstance(orig_inbound.returned_feedback, list):
                orig_inbound.returned_feedback = [orig_inbound.returned_feedback]

            orig_inbound.returned_feedback.append(feedback_request["feedback"])
            # Need to flag dirty, since modifying JSON object
            # https://docs.sqlalchemy.org/en/14/orm/session_api.htm
            flag_modified(orig_inbound, "returned_feedback")
        else:
            orig_inbound.returned_feedback = [feedback_request["feedback"]]

        db.session.add(orig_inbound)
        db.session.commit()
        return "Success", 200


def generate_secret_keys():
    """
    Generate any secret keys needed
    """
    request_keys = {}

    request_keys["feedback_secret_key"] = b64encode(os.urandom(32)).decode("utf-8")
    request_keys["inbound_secret_key"] = b64encode(os.urandom(32)).decode("utf-8")

    return request_keys


def prepare_scoring_as_json(faqs, overall_scores, tag_scores):
    """
    Convert scores so it can be saved as JSON in Db. Also save spell corrected
    terms.
    """
    scoring_output = defaultdict(dict)

    if len(overall_scores) == 0 and len(tag_scores) == 0:
        return scoring_output

    n_faqs = len(faqs)

    if len(overall_scores) != n_faqs:
        raise ValueError(
            f"Lengths of `faqs` and `overall_scores` must "
            f"be equal but got lengths {n_faqs} and {len(overall_scores)}, "
        )

    ranks = np.argsort(np.argsort(overall_scores)[::-1]) + 1

    for i, faq in enumerate(faqs):
        scoring_output[faq.faq_id]["overall_score"] = str(overall_scores[i])
        scoring_output[faq.faq_id]["faq_title"] = faq.faq_title
        scoring_output[faq.faq_id]["faq_content_to_send"] = faq.content_to_send
        scoring_output[faq.faq_id]["rank"] = str(ranks[i])
        # Convert scoring[faq.faq_id] to have string values (to save in DB as JSON)

    return scoring_output


def save_inbound_to_db(incoming, scoring_output, json_return, secret_keys):
    """
    Saves the inbound request and (most of) the response in the Db.

    The actual `json_return` sent back to the user gets augmented further in
    `finalise_return_json`.

    Parameters
    ----------
    incoming: Dict
        the incoming JSON request as a dictionary.
    scoring_output: Dict
        the processed scoring results dict that can be saved as a JSON
    json_return: Dict
        the response dict
    secret_keys: Dict
        A dictionary of secret keys

    Returns
    -------
    inbound_id: int
        The id of the new record created in the Db
    """
    received_ts = datetime.utcnow()
    incoming_metadata = incoming.get("metadata")

    new_inbound_query = Inbound(
        # Inbound details
        **secret_keys,
        inbound_text=incoming["text_to_match"],
        inbound_metadata=incoming_metadata,
        inbound_utc=received_ts,
        # Processing details
        model_scoring=scoring_output,
        # Returned details
        returned_content=json_return,
        returned_utc=datetime.utcnow(),
    )
    db.session.add(new_inbound_query)
    db.session.commit()

    return new_inbound_query.inbound_id


def prepare_return_json(scoring_output, keys, return_scoring, page_number):
    """
    Prepare the json to be returned. Note that it also has the side effect of
    updating `scoring_output`.

    Parameters
    ----------
    scoring_output: Dict
        the processed scoring results dict that can be saved as a JSON
    keys: Dict
        A dictionary of secret keys
    return_scoring: bool
        If scoring should be sent back in the JSON response
    page_number: Int
        The page number to return

    Returns
    -------
    scoring_output: Dict
        With spell_correct
    """
    items_per_page = current_app.config["N_TOP_MATCHES_PER_PAGE"]

    if page_number < 1:
        top_matches_list = []
    else:
        top_matches_list = get_top_n_matches(
            scoring_output, items_per_page, (page_number - 1) * items_per_page
        )

    json_return = {}
    json_return["top_responses"] = top_matches_list
    json_return.update(keys)

    if return_scoring:
        json_return["scoring"] = scoring_output

    return json_return


def get_top_n_matches(scoring, n_top_matches, start_idx=0):
    """
    Gives a list of scores for each FAQ, return the top `n_top_matches` FAQs

    Parameters
    ----------
    scoring: Dict[int, Dict]
        Dict with faq_id as key and faq details and scores as values.
        See return value of `get_faq_scores_for_message`. Assumes that `scoring`
        is sorted from highest score to lowest score.
    n_top_matches: int
        the number of top matches to return
    start_idx: int, optional
        takes the `n_top_matches` starting the `start_idx`

    Returns
    -------
    List[Tuple(str, str, str)]
        A list of tuples of (faq_id, faq_content_to_send, faq_title).
    """
    # Sort and copy over top matches
    top_matches_list = []
    sorted_scoring = sorted(scoring, key=lambda x: int(scoring[x]["rank"]))

    for faq_id in sorted_scoring[start_idx : start_idx + n_top_matches]:
        content = [
            faq.content_to_send for faq in current_app.faqs if faq.faq_id == faq_id
        ][0]

        top_matches_list.append(
            (
                str(faq_id),
                scoring[faq_id]["faq_title"],
                content,
            )
        )

    return top_matches_list


def finalise_return_json(json_return, inbound_id, current_page, max_pages):
    """
    Create additional items in JSON returned. This also includes pagination links
    to previous and next page.

    Parameters
    ----------
    json_return: Dict
        The dictionary to update. This will be turned into a JSON by flask when the
        endpoint returns
    inbound_id: int
        The id for the Db row created
    current_page: int
        Page number that is being returned. Used to calculate previous and next page
        links
    max_pages: int
        The maximum number of pages possible

    Returns
    -------
    json_return: Dict
        updated dictionary to be returned as response

    Returns
    -------

    """

    json_return["inbound_id"] = str(inbound_id)
    if current_page < max_pages:
        json_return["next_page_url"] = url_for(
            "main.inbound_results_page",
            inbound_id=inbound_id,
            page_number=(current_page + 1),
            inbound_secret_key=json_return["inbound_secret_key"],
        )
    if current_page > 1:
        json_return["prev_page_url"] = url_for(
            "main.inbound_results_page",
            inbound_id=inbound_id,
            page_number=(current_page - 1),
            inbound_secret_key=json_return["inbound_secret_key"],
        )

    return json_return


def bad_feedback_schema(feedback_json):
    """
    Check if the feedback JSON is well formed.
    """

    if not isinstance(feedback_json, dict):
        return True
    if feedback_json.get("feedback_type") not in ["positive", "negative"]:
        return True
    if feedback_json["feedback_type"] == "positive":
        if "faq_id" not in feedback_json:
            return True
    if feedback_json["feedback_type"] == "negative":
        if ("faq_id" not in feedback_json) and ("page_number" not in feedback_json):
            return True
    return False
