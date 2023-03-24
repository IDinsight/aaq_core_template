"""
General utility functions
"""
import os
import tempfile
from collections import UserDict
from pathlib import Path

import boto3
import pandas as pd
import yaml
from gensim.models import KeyedVectors
from gensim.models.fasttext import load_facebook_vectors

from ..data_models import ContextualizationModel


def load_fasttext(folder, filename):
    """Load fasttext word embedding"""
    if os.getenv("GITHUB_ACTIONS") == "true":
        bucket = os.getenv("WORD2VEC_BINARY_BUCKET")
        s3 = boto3.resource("s3")

        with tempfile.NamedTemporaryFile() as tf:
            s3.Bucket(bucket).download_file(filename, tf.name)
            model = load_facebook_vectors(tf.name)
    else:
        full_path = Path(__file__).parents[3] / "data" / folder / filename
        model = load_facebook_vectors(full_path)

    return model


def load_w2v_binary(folder, filename):
    """load word2vec binary"""
    if os.getenv("GITHUB_ACTIONS") == "true":
        bucket = os.getenv("WORD2VEC_BINARY_BUCKET")
        path = f"s3://{bucket}/{filename}"
    else:
        path = Path(__file__).parents[3] / "data" / folder / filename

    model = KeyedVectors.load_word2vec_format(
        path,
        binary=True,
    )

    return model


MODEL_LOADING_FUNCS = {
    "w2v": load_w2v_binary,
    "fasttext": load_fasttext,
}


def load_word_embeddings_bin(folder, filename, model_type):
    """
    Load pretrained word2vec or fasttext model from either local mount or S3
    based on environment var.

    TODO: make into a pure function and take ENV as input
    TODO: Change env var to be VECTORS_BINARY_BUCKET since it is no longer just W2V
    """
    if model_type not in MODEL_LOADING_FUNCS:
        raise ValueError(
            f"Invalid `model_type`! Choose from {list(MODEL_LOADING_FUNCS.keys())}"
        )

    load_function = MODEL_LOADING_FUNCS[model_type]
    model = load_function(folder, filename)

    return model


def load_yaml_config(filename, config_subfolder=None):
    """
    Load generic yaml files from config and return dictionary
    """
    if config_subfolder:
        full_path = Path(__file__).parents[1] / "config/{}/{}".format(
            config_subfolder, filename
        )
    else:
        full_path = Path(__file__).parents[1] / "config/{}".format(filename)

    with open(full_path) as file:
        yaml_dict = yaml.full_load(file)

    return yaml_dict


def load_data_sources(key=None):
    """
    Load the yaml file containing all data sources
    """
    params = load_yaml_config("data_sources.yml")

    if key is not None:
        params = params[key]

    return params


def load_parameters(key=None):
    """
    Load parameters
    """
    params = load_yaml_config("parameters.yml")

    if key is not None:
        params = params[key]

    return params


def load_generic_dataset(data_source_name):
    """
    Load any dataset using the data_sources.yml name
    """
    data_sources = load_data_sources()
    my_data_source_info = data_sources[data_source_name]

    file_name = my_data_source_info["filename"]
    folder = my_data_source_info["folder"]
    args = my_data_source_info.get("args")
    file_type = file_name.split(".")[1]

    if args is None:
        args = {}

    path = Path(__file__).parents[2] / "data/{}/{}".format(folder, file_name)

    if file_type == "csv":
        dataset = pd.read_csv(path, **args)
    elif file_type == "dta":
        dataset = pd.read_stata(path, **args)
    elif file_type in ["xlsx", "xls"]:
        dataset = pd.read_excel(path, **args)
    else:
        raise NotImplementedError(
            "Cannot load file {} with extention {}".format(file_name, file_type)
        )

    return dataset


def get_postgres_uri(
    endpoint,
    port,
    database,
    username,
    password,
):
    """
    Returns PostgreSQL database URI given info and secrets
    """

    connection_uri = "postgresql://%s:%s@%s:%s/%s" % (
        username,
        password,
        endpoint,
        port,
        database,
    )

    return connection_uri


class DefaultEnvDict(UserDict):
    """
    Dictionary but uses env variables as defaults
    """

    def __missing__(self, key):
        """
        If `key` is missing, look for env variable with the same name.
        """

        value = os.getenv(key)
        if value is None:
            raise KeyError(f"{key} not found in dict or environment variables")
        return os.getenv(key)


def load_lang_ctx(app):
    """Get language contextualization config from database"""
    with app.app_context():
        lang_ctx = ContextualizationModel.query.filter_by(active=True).first()

    return lang_ctx
