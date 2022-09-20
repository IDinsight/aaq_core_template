"""
This file contains various scoring functions that reduce the cosine similarity
between the message and each tag in the faq to a score per message/faq pair.
"""


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
    List[Tuple(str, str, str)]
        A list of tuples of (faq_id, faq_content_to_send, faq_title).
    """
    matched_faq_ids = set()
    # Sort and copy over top matches
    top_matches_list = []
    sorted_scoring = sorted(
        scoring, key=lambda x: float(scoring[x]["overall_score"]), reverse=True
    )

    for faq_id in sorted_scoring[start_idx:]:
        if faq_id not in matched_faq_ids:
            top_matches_list.append(
                (
                    str(faq_id),
                    scoring[faq_id]["faq_title"],
                    scoring[faq_id]["faq_content_to_send"],
                )
            )
            matched_faq_ids.add(faq_id)

        if len(matched_faq_ids) == n_top_matches:
            break
    return top_matches_list
