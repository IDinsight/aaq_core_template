##############################################################################
# INBOUND ENDPOINTS
##############################################################################
import os
from base64 import b64encode
from datetime import datetime

from flask import current_app, request
from sqlalchemy.orm.attributes import flag_modified

from ..data_models import Inbound
from ..database_sqlalchemy import db
from ..prometheus_metrics import metrics
from . import main
from .auth import auth
from ..src import utils


@main.route("/inbound/check", methods=["POST"])
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
def inbound_check():
    """
    Handles inbound queries, matching messages to FAQs in database

    Parameters
    ----------
    request (request proxy; see https://flask.palletsprojects.com/en/1.1.x/reqcontext/)
        The request should be sent as JSON with fields:
        - text_to_match (required, string)
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
        - scoring: scoring dictionary, only returned if "return_scoring" == "true";
          further described in return_faq_matches
    """
    received_ts = datetime.utcnow()

    incoming = request.json
    if "metadata" in incoming:
        incoming_metadata = incoming["metadata"]
    else:
        incoming_metadata = None

    processed_message = current_app.text_preprocessor(incoming["text_to_match"])

    word_vector_scores, spell_corrected = current_app.faqt_model.score(
        processed_message
    )

    scoring_output = utils.get_faq_scores_for_message(
        processed_message, current_app.faqs, word_vector_scores
    )

    top_matches_list = utils.get_top_n_matches(
        scoring_output, current_app.faqt_model.n_top_matches
    )

    # Convert scoring to have string values (to save in DB as JSON)
    for id in scoring_output:
        scoring_output[id]["overall_score"] = str(scoring_output[id]["overall_score"])

        # Convert scoring[faq.faq_id] to have string values (to save in DB as JSON)
        scoring_output[id]["tag_cs"] = {
            key: str(val) for key, val in scoring_output[id]["tag_cs"].items()
        }

    scoring_output["spell_corrected"] = " ".join(spell_corrected)

    processed_ts = datetime.utcnow()
    feedback_secret_key = b64encode(os.urandom(32)).decode("utf-8")

    json_return = {}
    json_return["top_responses"] = top_matches_list
    json_return["feedback_secret_key"] = feedback_secret_key

    if ("return_scoring" in incoming) and (incoming["return_scoring"] == "true"):
        # "true" is lowercase in JSON
        json_return["scoring"] = scoring_output

    new_inbound_query = Inbound(
        # Inbound details
        feedback_secret_key=feedback_secret_key,
        inbound_text=incoming["text_to_match"],
        inbound_metadata=incoming_metadata,
        inbound_utc=received_ts,
        # Processing details
        model_scoring=scoring_output,
        # Returned details
        returned_content=json_return,
        returned_utc=processed_ts,
    )
    db.session.add(new_inbound_query)
    db.session.commit()

    json_return["inbound_id"] = new_inbound_query.inbound_id

    # Flask automatically calls jsonify
    return json_return


@main.route("/inbound/feedback", methods=["PUT"])
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
def inbound_feedback():
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
    feedback_request = request.json

    orig_inbound = Inbound.query.filter_by(
        inbound_id=feedback_request["inbound_id"]
    ).first()

    if orig_inbound is None:
        return "No Matches", 404
    elif orig_inbound.feedback_secret_key != feedback_request["feedback_secret_key"]:
        return "Incorrect Feedback Secret Key", 403

    if orig_inbound.returned_feedback:
        # BACKWARDS COMPATIBILITY
        # Previously, instead of maintaining orig_inbound.returned_feedback as a list,
        # we saved a dict. So we convert dict to [dict], so that we can append without
        # overwriting the original feedback.
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
