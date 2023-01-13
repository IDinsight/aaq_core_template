##############################################################################
# INTERNAL ENDPOINTS
##############################################################################
import sqlalchemy as sa
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from .. import refresh_faqs
from ..database_sqlalchemy import db
from ..prometheus_metrics import metrics
from ..src import utils
from . import main
from .auth import auth


@main.route("/healthcheck", methods=["GET"])
@metrics.do_not_track()
def healthcheck():
    """
    Checks all of things that could be wrong with setup (e.g. running a pre-built
    image), especially on client's end
    We don't check here that the image was built correctly (a lot of those checks
    are done implicitly)
    1. Can connect to DB
    2. Can refresh FAQs from DB
    3. There are FAQs in the correct format
    4. Model loaded correctly - has the word 'test' in it
    5. Inbounds table exists
       - TODO: Check that can insert inbounds
    """
    try:
        db.session.execute("SELECT 1;")
    except SQLAlchemyError:
        return "Failed database connection", 500

    try:
        refresh_faqs(current_app)
    except Exception:
        return "Failed to refresh FAQs (even after connecting to database)", 500

    if not current_app.faqs:
        return "No FAQs in database", 500
    model_name = utils.load_parameters("matching_model")
    if model_name != "huggingface_model":
        if "test" not in current_app.faqt_model.word_embedding_model:
            return "Model failure - the word 'test' is not in the model", 500
    engine = sa.create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
    insp = sa.inspect(engine)
    if not insp.has_table("inbounds"):
        return "Inbounds table doesn't exist", 500

    return "Healthy - all checks complete", 200


@main.route("/auth-healthcheck", methods=["GET"])
@auth.login_required
@metrics.do_not_track()
def auth_healthcheck():
    """
    Check if app can connect to DB
    """
    try:
        db.session.execute("SELECT 1;")
        return "Healthy - Can connect to DB", 200
    except SQLAlchemyError:
        return "Failed DB connection", 500


@main.route("/internal/refresh-faqs", methods=["GET"])
@auth.login_required
@metrics.do_not_track()
def refresh_faqs_endpoint():
    """
    Refresh FAQs from database
    Must be authenticated
    Currently, cron job within container calls this hourly
        Eventually want FAQ UI to call this when FAQs updated
    """
    n_faqs = refresh_faqs(current_app)
    return f"Successfully refreshed {n_faqs} FAQs", 200
