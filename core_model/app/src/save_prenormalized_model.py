import os
import sys

from app import load_word_embeddings_bin

if __name__ == "__main__":
    os.chdir(sys.path[0])

    model = load_word_embeddings_bin(
        "pretrained_wv_models", "GoogleNews-vectors-negative300.bin", "w2v"
    )
    model.init_sims(replace=True)
    model.save_word2vec_format(
        "../data/pretrained_wv_models/GoogleNews-vectors-negative300-prenorm.bin",
        binary=True,
    )
