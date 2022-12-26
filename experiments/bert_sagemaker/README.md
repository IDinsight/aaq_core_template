# BERT Sagemaker Notebooks

This is the folder synced with [AAQ BERT Sagemaker notebook instance](https://af-south-1.console.aws.amazon.com/sagemaker/home?region=af-south-1#/notebook-instances/aaq-bert-experiment).

## Notebooks
There are two notebooks for each experiment:
1. Data cleaning and pre-processing
    1. Cleans FAQs with associated synthetic questions.
    3. Merges cleaned FAQs to the validation data.
    4. Creates training and test data for Question-Answer matching and saves them on S3.
    4. Creates training and test data for Question-Qnswer matching and saves them on S3.
2. Training and evaluation
    * Uses the Sagemaker Huggingface SDK to run a training and batch transform jobs.

### Question-Answer relevance scoring with MomConnect data
* [1.1-sy-MC-preprocess_mc_data.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/1.1-sy-MC-preprocess_mc_data.ipynb)
* [2.6-sy-MC-question-answer-matching.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/2.6-sy-MC-question-answer-matching.ipynb).


### Question-Answer relevance scoring with YAL data
* [1.2-sy-YAL-preprocess_yal_for_q-a-matching.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/1.2-sy-YAL-preprocess_yal_for_q-a-matching.ipynb)
* [2.2-sy-YAL-question-answer-relevance-scoring.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/notebooks/2.2-sy-YAL-question-answer-relevance-scoring.ipynb)

### Question-Question semantic matching with YAL data
* [1.3-sy-preprocess_yal_for_q-q-matching.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/1.3-sy-preprocess_yal_for_q-q-matching.ipynb)
* [2.4-sy-YAL-question-question-matching.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/notebooks/2.4-sy-YAL-question-question-matching.ipynb)

### Question-Answer and Question-Question ensembling
See [this confluence page](https://idinsight.atlassian.net/wiki/spaces/PD/pages/2007367706/Adding+question-question+matching#Combining-QA-and-QQ-scores) for background.
* [3.2-sy-ensemble_QA_and_QQ.ipynb](https://github.com/IDinsight/aaq_core_template/blob/experiments/experiments/bert_sagemaker/notebooks/notebooks/3.2-sy-ensemble_QA_and_QQ.ipynb)