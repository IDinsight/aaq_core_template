"""
# MODEL CONFIG ENDPOINTS
"""

from flask import current_app

from .. import get_text_preprocessor
from ..prometheus_metrics import metrics
from ..src.utils import load_language_context
from . import main
from .auth import auth


@main.route("/config/edit-language-context", methods=["GET"])
@auth.login_required
@metrics.do_not_track()
def edit_language_context():
    """
    Update faqt model language contexts with the current configuration in the database
    """
    language_context = load_language_context(current_app)

    current_app.faqt_model.set_glossary(
        language_context.custom_wvs if language_context else {}
    )

    current_app.faqt_model.set_tokenizer(
        get_text_preprocessor(
            language_context.pairwise_triplewise_entities if language_context else {}
        )
    )
    current_app.faqt_model.set_tags_guiding_typos(
        language_context.tag_guiding_typos if language_context else []
    )
    if language_context is None:
        return "Empty"
    else:
        return language_context.version_id
