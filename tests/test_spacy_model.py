from presidio_evaluator.data_generator import read_synth_dataset
from presidio_evaluator.evaluation import Evaluator
from presidio_evaluator.models.spacy_model import SpacyModel
import numpy as np


def test_spacy_simple():
    import os
    dir_path = os.path.dirname(os.path.realpath(__file__))
    input_samples = read_synth_dataset(os.path.join(dir_path, "data/generated_small.txt"))

    spacy_model = SpacyModel(model_name="en_core_web_lg", entities_to_keep=['PERSON'])
    evaluator = Evaluator(model=spacy_model)
    evaluation_results = evaluator.evaluate_all(input_samples)
    scores = evaluator.calculate_score(evaluation_results)

    np.testing.assert_almost_equal(scores.pii_precision, scores.entity_precision_dict['PERSON'])
    np.testing.assert_almost_equal(scores.pii_recall, scores.entity_recall_dict['PERSON'])
    assert scores.pii_recall > 0
    assert scores.pii_precision > 0
