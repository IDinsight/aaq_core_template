"""
Main python script called by gunicorn
"""
import logging
import os

import sentry_sdk
from app import create_app, db, init_faqt_model, refresh_faqs
from app.data_models import FAQModel, Inbound
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# Log at WARNING level to capture timestamps when FAQs are refreshed
sentry_logging = LoggingIntegration(event_level=logging.WARNING)
sentry_sdk.init(
    integrations=[FlaskIntegration(), sentry_logging],
    traces_sample_rate=os.environ.get("SENTRY_TRANSACTIONS_SAMPLE_RATE"),
)

app = create_app()
init_faqt_model(app)
refresh_faqs(app)


@app.shell_context_processor
def make_shell_context():
    """
    Return flask shell with objects imported
    """
    return dict(db=db, Inbound=Inbound, FAQModel=FAQModel)
