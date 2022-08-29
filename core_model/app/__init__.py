"""
Create and initialise the app. Uses Blueprints to define view.
"""
import os
from functools import partial

from faqt.model import KeyedVectorsScorer
from faqt.preprocessing import preprocess_text_for_word_embedding
from faqt.scoring_functions import cs_nearest_k_percent_average
from flask import Flask
from hunspell import Hunspell

from .data_models import FAQModel
from .database_sqlalchemy import db
from .prometheus_metrics import metrics
from .src.faq_weights import add_faq_weight_share
from .src.utils import (
    DefaultEnvDict,
    get_postgres_uri,
    load_custom_wvs,
    load_data_sources,
    load_pairwise_entities,
    load_parameters,
    load_tags_guiding_typos,
    load_word_embeddings_bin,
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
            "pool_size": 10,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
        **config,
    )

    db.init_app(app)
    metrics.init_app(app)

    app.faqt_model = create_faqt_model(config)
    app.text_preprocessor = get_text_preprocessor()

    refresh_faqs(app)


def get_config_data(params):
    """
    If parameter exists in `params` use that else use env variables.
    """

    config = DefaultEnvDict()
    app_config = load_parameters("score_reduction")
    text_preprocessor_config = load_parameters("preprocessing")
    config["matching_model"] = load_parameters("matching_model")
    config.update(app_config)
    config.update(text_preprocessor_config)
    config.update(params)

    config["SQLALCHEMY_DATABASE_URI"] = get_postgres_uri(
        config["PG_ENDPOINT"],
        config["PG_PORT"],
        config["PG_DATABASE"],
        config["PG_USERNAME"],
        config["PG_PASSWORD"],
    )

    return config


def load_embeddings(name_of_model_in_data_source):
    """
    Load the correct embeddings
    """

    model_to_use_name = name_of_model_in_data_source

    data_sources = load_data_sources()

    model_folder = data_sources[model_to_use_name]["folder"]
    model_filename = data_sources[model_to_use_name]["filename"]
    model_type = data_sources[model_to_use_name]["type"]

    w2v_model = load_word_embeddings_bin(
        model_folder,
        model_filename,
        model_type,
    )

    return w2v_model


def create_faqt_model(config):
    """
    Create a new instance of the faqt class.
    """

    gensim_keyed_vector = load_embeddings(config["matching_model"])
    faqs_params = load_parameters("faq_match")
    custom_wvs = load_custom_wvs()
    tags_guiding_typos = load_tags_guiding_typos()
    hunspell = Hunspell()

    scoring_function_args = config["scoring_function_args"]
    n_top_matches = faqs_params["n_top_matches_per_page"]

    return KeyedVectorsScorer(
        gensim_keyed_vector,
        glossary=custom_wvs,
        hunspell=hunspell,
        tags_guiding_typos=tags_guiding_typos,
        n_top_matches=n_top_matches,
        scoring_function=cs_nearest_k_percent_average,
        scoring_func_kwargs=scoring_function_args,
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
    app.faqs = add_faq_weight_share(faqs)
    app.faqt_model.set_tags([faq.faq_tags for faq in faqs])

    return len(faqs)
