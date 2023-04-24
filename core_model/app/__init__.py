"""
Create and initialise the app. Uses Blueprints to define view.
"""
import os
from functools import partial

from faqt import WMDScorer, preprocess_text_for_word_embedding
from faqt.model.faq_matching.contextualization import (
    Contextualization,
    get_ordered_distance_matrix,
)
from flask import Flask
from hunspell import Hunspell

from .data_models import FAQModel
from .database_sqlalchemy import db, migrate
from .prometheus_metrics import metrics
from .src.faq_weights import add_faq_weight_share
from .src.utils import (
    DefaultEnvDict,
    deep_update,
    get_postgres_uri,
    load_data_sources,
    load_language_context,
    load_parameters,
    load_word_embeddings_bin,
)


def create_app(override_params=None):
    """
    Factory to create a new flask app instance
    """
    app = Flask(__name__)
    setup(app, override_params)

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    return app


def setup(app, override_params):
    """
    Add config to app and initialise extensions.

    Parameters
    ----------
    app : Flask app
        A newly created flask app
    override_params : Dict
        A dictionary with config parameters
    """

    if override_params is None:
        override_params = {}

    config = get_config_data(override_params)

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
    migrate.init_app(app, db)

    app.is_context_active = app.config["CONTEXT_ACTIVE"]


def get_config_data(override_params):
    """
    Loads parameters from `parameters.yaml` and updates with values
    in `override_params` if any.

    Returns a `DefaultEnvDict` which looks for the key in environment variables
    if not found in the dictionary.
    """

    parameters = load_parameters()
    parameters = deep_update(parameters, override_params)

    config = DefaultEnvDict()

    config["PREPROCESSING_PARAMS"] = parameters["preprocessing"]
    # saved for reference
    model_name = parameters["matching_model"]
    config["MODEL_PARAMS"] = parameters["model_params"][model_name]
    config["MATCHING_MODEL"] = model_name
    config["CONTEXT_ACTIVE"] = parameters["contextualization"]["active"]
    faq_matching_config = parameters["faq_match"]
    config.update(faq_matching_config)

    config["SQLALCHEMY_DATABASE_URI"] = get_postgres_uri(
        config["PG_ENDPOINT"],
        config["PG_PORT"],
        config["PG_DATABASE"],
        config["PG_USERNAME"],
        config["PG_PASSWORD"],
    )

    return config


def create_contextualization(app, context_list):
    """Create demographic contextualization object"""
    contexts = load_parameters("contextualization")[context_list]
    distance_matrix = get_ordered_distance_matrix(contexts)
    faq_contexts = {
        faq.faq_id: faq.faq_contexts if faq.faq_contexts is not None else contexts
        for faq in app.faqs
    }
    app.contextualizer = Contextualization(
        contents_dict=faq_contexts, distance_matrix=distance_matrix
    )
    app.context_list = contexts


def load_embeddings(name_of_model_in_data_source):
    """
    Load the correct embeddings
    """

    model_to_use_name = name_of_model_in_data_source

    data_sources = load_data_sources()

    model_folder = data_sources[model_to_use_name]["folder"]
    model_filename = data_sources[model_to_use_name]["filename"]
    model_type = data_sources[model_to_use_name]["type"]

    word_embedding_model = load_word_embeddings_bin(
        model_folder,
        model_filename,
        model_type,
    )

    return word_embedding_model


def init_faqt_model(app):
    """
    Create a new instance of the faqt model.
    """

    gensim_keyed_vector = load_embeddings(app.config["MATCHING_MODEL"])
    language_context = load_language_context(app)
    custom_wvs = language_context.custom_wvs if language_context else {}
    pairwise = language_context.pairwise_triplewise_entities if language_context else {}
    tags_guiding_typos = language_context.tag_guiding_typos if language_context else []
    hunspell = Hunspell()

    params = app.config["MODEL_PARAMS"]

    app.faqt_model = WMDScorer(
        gensim_keyed_vector,
        tokenizer=get_text_preprocessor(pairwise),
        weighting_method=params["weighting_method"],
        weighting_kwargs=params["weighting_kwargs"],
        glossary=custom_wvs,
        hunspell=hunspell,
        tags_guiding_typos=tags_guiding_typos,
    )


def get_text_preprocessor(pairwise_entities):
    """
    Return a partial function that takes one argument - the raw function
    to be processed.
    """

    pp_params = load_parameters("preprocessing")
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
    content = [faq.faq_content_to_send for faq in faqs]
    weights = [faq.faq_weight_share for faq in faqs]
    app.faqt_model.set_contents(content, weights)
    if app.is_context_active:
        create_contextualization(app, "context_list")
    return len(faqs)
