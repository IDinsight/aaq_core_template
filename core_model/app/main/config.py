"""
# MODEL CONFIG ENDPOINTS
"""

from flask import current_app

from .. import refresh_language_context
from ..prometheus_metrics import metrics
from . import main
from .auth import auth


@main.route("/config/edit-language-context", methods=["GET"])
@auth.login_required
@metrics.do_not_track()
def edit_language_context():
    """
    Update faqt model language contexts with the current configuration in the database
    """
    version = refresh_language_context(current_app)

    return version
