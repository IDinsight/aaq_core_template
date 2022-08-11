"""
This file contains various scoring functions that reduce the cosine similarity
between the message and each tag in the faq to a score per message/faq pair.
"""
import numpy as np

SCORE_REDUCTION_METHODS = {}


def get_faq_scores_for_message(
    inbound_vectors,
    faqs,
    scores,
    reduction_func,
    **reduction_func_arg,
):
    """
    Returns scores for the inbound vectors against each faq

    Parameters
    ----------
    inbound_vectors: List[Array]
        List of inbound tokens as word vectors
    faqs: List[FAQ]
        A list of faq-like objects. Each FAQ object must contain word vectors for
        each tags as a dictionary under `FAQ.tags_wvs`
    scores: List[Dict[str, int]]
        A list with an item for each FAQ. Each item is a dictionary with keys as tags
        and values as the cosine similarity metric between incoming message and the tag
    reduction_func: str
        Name of one of the score reduction functions that reduce cosine similarity
        between message and each faq tag to a score for each message/faq combination.
    reduction_func_arg: Dict
        Additional arguments to be send to `reduction_func`

    Returns
    -------
    Dict[int, Dict]
        A Dictionary with `faq_id` as key. Values: faq details including scores
        for each tag and an `overall_score`
    """

    scoring = {}

    scoring_method = SCORE_REDUCTION_METHODS.get(reduction_func)
    if scoring_method is None:
        all_scoring_methods = SCORE_REDUCTION_METHODS.keys()
        raise NotImplementedError(
            (
                f"Score reduction function: `{score_reduction_func}`"
                f" not implemented. Must be one of {all_scoring_methods}"
            )
        )
    for faq, faq_score in zip(faqs, scores):
        scoring[faq.faq_id] = {}
        scoring[faq.faq_id]["faq_title"] = faq.faq_title
        scoring[faq.faq_id]["faq_content_to_send"] = faq.faq_content_to_send
        scoring[faq.faq_id]["tag_cs"] = faq_score

        cs_values = list(scoring[faq.faq_id]["tag_cs"].values())
        scoring[faq.faq_id]["overall_score"] = scoring_method(
            cs_values, weight=faq.faq_weight_share, **reduction_func_arg
        )

    return scoring


def get_top_n_matches(scoring, n_top_matches, start_idx=0):
    """
    Gives a list of scores for each FAQ, return the top `n_top_matches` FAQs

    Parameters
    ----------
    scoring: Dict[int, Dict]
        Dict with faq_id as key and faq details and scores as values.
        See return value of `get_faq_scores_for_message`. Assumes that `scoring`
        is sorted from highest score to lowest score.
    n_top_matches: int
        the number of top matches to return
    start_idx: int, optional
        takes the `n_top_matches` starting the `start_idx`

    Returns
    -------
    List[Tuple(int, str)]
        A list of tuples of (faq_id, faq_content_to_send)._
    """
    matched_faq_titles = set()
    # Sort and copy over top matches
    top_matches_list = []
    sorted_scoring = sorted(
        scoring, key=lambda x: float(scoring[x]["overall_score"]), reverse=True
    )
    for id in sorted_scoring[start_idx:]:
        if scoring[id]["faq_title"] not in matched_faq_titles:
            top_matches_list.append(
                (scoring[id]["faq_title"], scoring[id]["faq_content_to_send"])
            )
            matched_faq_titles.add(scoring[id]["faq_title"])

        if len(matched_faq_titles) == n_top_matches:
            break
    return top_matches_list


def score_reduction_func(scoring_func):
    """
    Decorator to register scoring functions
    """
    SCORE_REDUCTION_METHODS[scoring_func.__name__] = scoring_func
    return scoring_func


@score_reduction_func
def avg_min_mean(cs_values, **kwargs):
    """Original scoring: mean of avg and min"""
    return (np.mean(cs_values) + np.min(cs_values)) / 2


@score_reduction_func
def simple_mean(cs_values, **kwargs):
    """Simple mean of cs values"""
    return np.mean(cs_values)


@score_reduction_func
def mean_plus_weight(cs_values, weight, N, **kwargs):
    """Simple mean plus N * weights"""
    return (simple_mean(cs_values) + N * weight) / (N + 1)
