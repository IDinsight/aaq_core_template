"""
Datamodels used in the app
"""

from .database_sqlalchemy import db


class Inbound(db.Model):
    """
    SQLAlchemy data model for Inbound API calls (with model and return metadata)
    """

    __tablename__ = "inbounds"

    inbound_id = db.Column(db.Integer(), primary_key=True)
    feedback_secret_key = db.Column(db.String())
    inbound_text = db.Column(db.String())
    inbound_metadata = db.Column(db.JSON())
    inbound_utc = db.Column(db.DateTime())

    model_scoring = db.Column(db.JSON())

    returned_content = db.Column(db.JSON())
    returned_utc = db.Column(db.DateTime())
    returned_feedback = db.Column(db.JSON())

    def __repr__(self):
        """Pretty print"""
        return "<Inbound %r>" % self.inbound_id


class FAQModel(db.Model):
    """
    SQLAlchemy data model for FAQ
    """

    __tablename__ = "faqmatches"

    faq_id = db.Column(db.Integer, primary_key=True)
    faq_added_utc = db.Column(db.DateTime())
    faq_updated_utc = db.Column(db.DateTime())
    faq_author = db.Column(db.String())
    faq_title = db.Column(db.String())
    faq_content_to_send = db.Column(db.String())
    faq_tags = db.Column(db.ARRAY(db.String()))
    faq_thresholds = db.Column(db.ARRAY(db.Float()))
    faq_weight = db.Column(db.Integer())

    def __repr__(self):
        """Pretty print"""
        return "<FAQ %r>" % self.faq_id


class TemporaryModel:
    """
    Custom class to use for temporary models. Used as a drop in for other
    db.Model classes. Useful when we don't want to create a record in the Db
    (e.g. checking new tags)
    """

    def __init__(self, **kwargs):
        """Update internal properties"""
        self.__dict__.update(kwargs)
