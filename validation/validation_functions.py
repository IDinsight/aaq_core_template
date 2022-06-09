"""
Validation scripts
"""
import os
import sys
from datetime import datetime

import pandas as pd
from app.src.utils import (
    load_custom_wvs,
    load_pairwise_entities,
    load_tags_guiding_typos,
)
from faqt.model.embeddings import (
    load_wv_pretrained_bin,
    model_search,
    model_search_word,
)
from hunspell import Hunspell


class FAQ:
    """
    Class for FAQ objects (to replicate functionality of SQLAlchemy ORM)
    """

    def __init__(self, title, faq_tags_wvs, faq_id):
        """
        Create FAQ object
        """
        self.faq_id = faq_id
        self.faq_tags_wvs = faq_tags_wvs
        self.faq_thresholds = [0] * len(faq_tags_wvs)

        self.faq_title = title
        self.faq_content_to_send = None


def validation_wrapper(df_test, df_faq):
    """
    Returns single/top 3 accuracy in df_test, using FAQs in df_faq
    """
    #################### Load model components ####################
    model_package = {}
    model_package["model"] = load_wv_pretrained_bin(
        "pretrained_wv_models",
        "GoogleNews-vectors-negative300-prenorm.bin",
    )
    model_package["custom_wvs"] = load_custom_wvs()
    model_package["pairwise_entities"] = load_pairwise_entities()
    model_package["hunspell"] = Hunspell()

    tags_guiding_typos_raw = load_tags_guiding_typos()
    tags_guiding_typos_wv = model_search(
        tags_guiding_typos_raw, model_package["model"], model_package["custom_wvs"]
    )
    model_package["tags_guiding_typos_wv"] = tags_guiding_typos_wv

    model_package["parameters"] = {}
    model_package["parameters"]["n_min_dashed_words_url"] = 0
    model_package["parameters"]["k"] = 10
    model_package["parameters"]["floor"] = 1
    model_package["parameters"]["n_top_matches"] = 3

    #################### Save all FAQs ####################
    def concat_tags(row):
        """combine row items into list"""
        return list(row[1:].dropna())

    df_faq["tags"] = df_faq.apply(concat_tags, axis=1)

    faqs = []
    for index, row in df_faq.iterrows():
        tag_wvs = {
            tag: model_search_word(
                tag, model_package["model"], model_package["custom_wvs"]
            )
            for tag in row["tags"]
        }
        faqs.append(FAQ(row["topic"], tag_wvs, index))

    #################### Run model ####################
    return basic_accuracy(df_test, faqs, model_package)


def run_validation_scoring(
    df_test_source, df_faq_source, true_label_column, query_column
):
    """
    Run validation
    """
    scoring = {}
    return scoring
