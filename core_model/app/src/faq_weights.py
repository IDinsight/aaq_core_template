"""Functions for calculating faq weights"""


def add_faq_weight_share(faqs):
    """
    Add a new field `faq_weight_share` which is a normalised value of
    `faq_weight`. It ensures `faq_weight_share` adds to one.

    Parameters
    ----------
    faqs : List[FAQ]
        A list FAQ ORM objects

    Returns
    -------
    A list of FAQ ORM objects
    """

    total_weight = sum([f.faq_weight for f in faqs])

    for faq in faqs:
        faq.faq_weight_share = faq.faq_weight / total_weight

    return faqs
