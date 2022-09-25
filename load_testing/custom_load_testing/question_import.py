import os
import string
import sys

import numpy as np
import pandas as pd


def load_questions(abs_filepath):
    """
    Load questions from file.
    Params:
        filepath: path to CSV file containing questions
    Returns:
        questions_df (pd.DataFrame): dataframe of questions loaded from file
    """

    print("Loading questions from file...")
    # os.chdir(sys.path[0])
    questions_df = pd.read_csv(abs_filepath, index_col=0)
    questions_df.rename(
        {"Question": "question", "FAQ Name": "faq_name", "Urgent": "urgent"},
        axis=1,
        inplace=True,
    )

    return questions_df


def generate_typo(sentence, p_delete, p_insert, p_replace):
    """
    [From Adam's load-testing]
    Generate typos in sentence, character by character using given with probabilities.

    Args:
        sentence (str): sentence to generate typos in
        p_delete (float): probability of deleting character
        p_insert (float): probability of inserting character (50% probability of inserting character before or after)
        p_replace (float): probability of replacing character
    Returns:
        sentence (str): sentence with typos
    """

    nearby_keys = {
        "a": ["q", "w", "s", "x", "z"],
        "b": ["v", "g", "h", "n"],
        "c": ["x", "d", "f", "v"],
        "d": ["s", "e", "r", "f", "c", "x"],
        "e": ["w", "s", "d", "r"],
        "f": ["d", "r", "t", "g", "v", "c"],
        "g": ["f", "t", "y", "h", "b", "v"],
        "h": ["g", "y", "u", "j", "n", "b"],
        "i": ["u", "j", "k", "o"],
        "j": ["h", "u", "i", "k", "n", "m"],
        "k": ["j", "i", "o", "l", "m"],
        "l": ["k", "o", "p"],
        "m": ["n", "j", "k", "l"],
        "n": ["b", "h", "j", "m"],
        "o": ["i", "k", "l", "p"],
        "p": ["o", "l"],
        "q": ["w", "a", "s"],
        "r": ["e", "d", "f", "t"],
        "s": ["w", "e", "d", "x", "z", "a"],
        "t": ["r", "f", "g", "y"],
        "u": ["y", "h", "j", "i"],
        "v": ["c", "f", "g", "v", "b"],
        "w": ["q", "a", "s", "e"],
        "x": ["z", "s", "d", "c"],
        "y": ["t", "g", "h", "u"],
        "z": ["a", "s", "x"],
        " ": ["c", "v", "b", "n", "m"],
    }

    all_keys = list(string.ascii_uppercase + string.ascii_lowercase + " ,.")

    new_sentence = ""
    prob = np.random.uniform(size=len(sentence))

    delete_cutoff = p_delete
    insert_before_cutoff = delete_cutoff + p_insert / 2
    insert_after_cutoff = insert_before_cutoff + p_insert / 2
    replace_cutoff = insert_after_cutoff + p_replace

    for i, s in enumerate(sentence):
        p = prob[i]

        # For insertions and replacements, use a character from nearby_keys
        # if the current character appears in nearby_keys.
        # If not, use a random ASCII character.
        if p < delete_cutoff:
            pass
        elif p < insert_before_cutoff:
            if s in nearby_keys:
                new_sentence += np.random.choice(nearby_keys[s]) + s
            else:
                new_sentence += np.random.choice(all_keys) + s
        elif p < insert_after_cutoff:
            if s in nearby_keys:
                new_sentence += s + np.random.choice(nearby_keys[s])
            else:
                new_sentence += s + np.random.choice(all_keys)
        elif p < replace_cutoff:
            if s in nearby_keys:
                new_sentence += np.random.choice(nearby_keys[s])
            else:
                new_sentence += np.random.choice(all_keys)
        else:
            new_sentence += s

    return new_sentence


def select_a_question(questions_df, add_typo=False):
    """
    Randomly selects a question from the dataframe and returns the question_msg_id, question, faq_name, urgent.

    Args:
        questions_df (pd.DataFrame): dataframe of questions
        add_typo (bool): whether to add typos to the question
    Returns:
        question_msg_id (str): message ID of question
        question (str): question (with added typos if add_typo=True)
        faq_name (str): FAQ name
        urgent (bool): whether question is urgent
    """
    df_val_row = questions_df.sample(1).values[0]
    question_msg_id, question, faq_name, urgent = df_val_row

    if add_typo:
        question = generate_typo(question, p_delete=0.02, p_insert=0.02, p_replace=0.02)

    return question
