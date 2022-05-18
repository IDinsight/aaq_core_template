"""
Create and initialise the app. Uses Blueprints to define view.
"""
import os
from functools import partial

from faqt.model import FAQScorer
from faqt.preprocessing import preprocess_text_for_word_embedding
from faqt.scoring_functions import cs_nearest_k_percent_average
from flask import Flask
from hunspell import Hunspell

from .data_models import FAQModel
from .database_sqlalchemy import db
from .prometheus_metrics import metrics
from .src.utils import (
    DefaultEnvDict,
    get_postgres_uri,
    load_custom_wvs,
    load_data_sources,
    load_pairwise_entities,
    load_parameters,
    load_tags_guiding_typos,
    load_wv_pretrained_bin,
)


def create_app(params=None):
    """
    Factory to create a new flask app instance
    """
    app = Flask(__name__)
    setup(app, params)

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    return app


def setup(app, params):
    """
    Add config to app and initialise extensions.

    Parameters
    ----------
    app : Flask app
        A newly created flask app
    params : Dict
        A dictionary with config parameters
    """

    if params is None:
        params = {}

    config = get_config_data(params)

    app.config.from_mapping(
        JSON_SORT_KEYS=False,
        SECRET_KEY=os.urandom(24),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
        **config,
    )

    db.init_app(app)
    metrics.init_app(app)

    app.faqt_model = create_faqt_model()
    app.text_preprocessor = get_text_preprocessor()

    refresh_faqs(app)


def get_config_data(params):
    """
    If parameter exists in `params` use that else use env variables.
    """

    config = DefaultEnvDict()
    config.update(params)

    config["SQLALCHEMY_DATABASE_URI"] = get_postgres_uri(
        config["PG_ENDPOINT"],
        config["PG_PORT"],
        config["PG_DATABASE"],
        config["PG_USERNAME"],
        config["PG_PASSWORD"],
    )

    return config


def create_faqt_model():
    """
    Create a new instance of the faqt class.
    """
    data_sources = load_data_sources()
    w2v_model = load_wv_pretrained_bin(
        data_sources["google_news_pretrained"]["folder"],
        data_sources["google_news_pretrained"]["filename"],
    )
    pp_params = load_parameters("preprocessing")
    faqs_params = load_parameters("faq_match")
    custom_wvs = load_custom_wvs()
    tags_guiding_typos = load_tags_guiding_typos()
    hunspell = Hunspell()

    scoring_function_args = pp_params["scoring_function_args"]
    n_top_matches = faqs_params["n_top_matches"]

    return FAQScorer(
        w2v_model,
        glossary=custom_wvs,
        hunspell=hunspell,
        tags_guiding_typos=tags_guiding_typos,
        n_top_matches=n_top_matches,
        scoring_function=cs_nearest_k_percent_average,
        **scoring_function_args,
    )


def get_text_preprocessor():
    """
    Return a partial function that takes one argument - the raw function
    to be processed.
    """

    pp_params = load_parameters("preprocessing")
    pairwise_entities = load_pairwise_entities()
    n_min_dashed_words_url = pp_params["min_dashed_words_to_parse_text_from_url"]
    reincluded_stop_words = pp_params["reincluded_stop_words"]

    text_preprocessor = partial(
        preprocess_text_for_word_embedding,
        entities_dict=pairwise_entities,
        n_min_dashed_words_url=n_min_dashed_words_url,
        reincluded_stop_words=reincluded_stop_words,
    )

    return text_preprocessor


def refresh_faqs(app):
    """
    Queries DB for FAQs, and attaches to app.faqs for use with model
    """

    # Need to push application context. Otherwise will raise:
    # RuntimeError: No application found.
    # Either work inside a view function or push an application context.
    # See http://flask-sqlalchemy.pocoo.org/contexts/.

    with app.app_context():
        faqs = FAQModel.query.all()
    faqs.sort(key=lambda x: x.faq_id)
    app.faqs = faqs
    app.faqt_model.set_tags(faqs)

    return len(faqs)
