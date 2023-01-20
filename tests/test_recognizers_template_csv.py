import numpy as np
import pytest
from presidio_analyzer.predefined_recognizers import CreditCardRecognizer

from presidio_evaluator import InputSample
from presidio_evaluator.data_generator import PresidioSentenceFaker
from presidio_evaluator.evaluation.scorers import score_presidio_recognizer


class TemplateTextTestCase:
    """
    Test case parameters for tests with dataset generated from a template and csv values
    """

    def __init__(
            self,
            test_name,
            pii_csv,
            utterances,
            num_of_examples,
            acceptance_threshold,
            marks,
    ):
        self.test_name = test_name
        self.pii_csv = pii_csv
        self.utterances = utterances
        self.num_of_examples = num_of_examples
        self.acceptance_threshold = acceptance_threshold
        self.marks = marks

    def to_pytest_param(self):
        return pytest.param(
            self.pii_csv,
            self.utterances,
            self.num_of_examples,
            self.acceptance_threshold,
            id=self.test_name,
            marks=self.marks,
        )


# template-dataset test cases
cc_test_template_testdata = [
    # large dataset fixture. marked as slow
    TemplateTextTestCase(
        test_name="fake-names-100",
        pii_csv="{}/data/FakeNameGenerator.com_100.csv",
        utterances="{}/data/templates.txt",
        num_of_examples=100,
        acceptance_threshold=0.9,
        marks=pytest.mark.slow,
    )
]


# credit card recognizer tests on template-generates data
@pytest.mark.parametrize(
    "pii_csv, " "utterances, " "num_of_examples, " "acceptance_threshold",
    [testcase.to_pytest_param() for testcase in cc_test_template_testdata],
)
def test_credit_card_recognizer_with_template(
        pii_csv, utterances, num_of_examples, acceptance_threshold
):
    """
    Test credit card recognizer with a dataset generated from
    template and a CSV values file
    :param pii_csv: input csv file location
    :param utterances: template file location
    :param num_of_examples: number of samples to be used from dataset
    to test
    :param acceptance_threshold: minimum precision/recall
     allowed for tests to pass
    """
    import os

    dir_path = os.path.dirname(os.path.realpath(__file__))

    templates = utterances.format(dir_path)
    sentence_faker = PresidioSentenceFaker('en_US', lower_case_ratio=0.05, sentence_templates=templates)
    examples = sentence_faker.generate_new_fake_sentences(num_of_examples)
    input_samples = [
        InputSample.from_faker_spans_result(example) for example in examples
    ]

    scores = score_presidio_recognizer(
        recognizer=CreditCardRecognizer(),
        entities_to_keep=["CREDIT_CARD"],
        input_samples=input_samples,
    )
    if not np.isnan(scores.pii_f):
        assert acceptance_threshold <= scores.pii_f
