from collections import Counter

import numpy as np
import pytest

from presidio_evaluator import InputSample, Span

from presidio_evaluator.evaluation import EvaluationResult, Evaluator, ErrorType
from tests.mocks import (
    IdentityTokensMockModel,
    FiftyFiftyIdentityTokensMockModel,
    MockTokensModel,
)


def test_evaluator_simple():
    prediction = ["O", "O", "O", "U-ANIMAL"]
    model = MockTokensModel(prediction=prediction, entities_to_keep=["ANIMAL"])

    evaluator = Evaluator(model=model)
    sample = InputSample(
        full_text="I am the walrus", masked="I am the [ANIMAL]", spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus"]
    sample.tags = ["O", "O", "O", "U-ANIMAL"]

    evaluated = evaluator.evaluate_sample(sample, prediction)
    final_evaluation = evaluator.calculate_score([evaluated])

    assert final_evaluation.pii_precision == 1
    assert final_evaluation.pii_recall == 1


def test_evaluate_sample_wrong_entities_to_keep_correct_statistics():
    prediction = ["O", "O", "O", "U-ANIMAL"]
    model = MockTokensModel(prediction=prediction)

    evaluator = Evaluator(model=model, entities_to_keep=["SPACESHIP"])

    sample = InputSample(
        full_text="I am the walrus", masked="I am the [ANIMAL]", spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus"]
    sample.tags = ["O", "O", "O", "U-ANIMAL"]

    evaluated = evaluator.evaluate_sample(sample, prediction)
    assert evaluated.results[("O", "O")] == 4


def test_evaluate_same_entity_correct_statistics():
    prediction = ["O", "U-ANIMAL", "O", "U-ANIMAL"]
    model = MockTokensModel(prediction=prediction)
    evaluator = Evaluator(model=model, entities_to_keep=["ANIMAL"], skip_words=["-"])
    sample = InputSample(
        full_text="I dog the walrus", masked="I [ANIMAL] the [ANIMAL]", spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus"]
    sample.tags = ["O", "O", "O", "U-ANIMAL"]

    evaluation_result = evaluator.evaluate_sample(sample, prediction)
    assert evaluation_result.results[("O", "O")] == 2
    assert evaluation_result.results[("ANIMAL", "ANIMAL")] == 1
    assert evaluation_result.results[("O", "ANIMAL")] == 1


def test_evaluate_multiple_entities_to_keep_correct_statistics():
    prediction = ["O", "U-ANIMAL", "O", "U-ANIMAL"]
    entities_to_keep = ["ANIMAL", "PLANT", "SPACESHIP"]
    model = MockTokensModel(prediction=prediction)
    evaluator = Evaluator(
        model=model, entities_to_keep=entities_to_keep, skip_words=["-"]
    )

    sample = InputSample(
        full_text="I dog the walrus", masked="I [ANIMAL] the [ANIMAL]", spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus"]
    sample.tags = ["O", "O", "O", "U-ANIMAL"]

    evaluation_result = evaluator.evaluate_sample(sample, prediction)
    assert evaluation_result.results[("O", "O")] == 2
    assert evaluation_result.results[("ANIMAL", "ANIMAL")] == 1
    assert evaluation_result.results[("O", "ANIMAL")] == 1


def test_evaluate_multiple_tokens_correct_statistics():
    prediction = ["O", "O", "O", "B-ANIMAL", "I-ANIMAL", "L-ANIMAL"]
    model = MockTokensModel(prediction=prediction)
    evaluator = Evaluator(model=model, entities_to_keep=["ANIMAL"])
    sample = InputSample(
        "I am the walrus amaericanus magnifico", masked=None, spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus", "americanus", "magnifico"]
    sample.tags = ["O", "O", "O", "B-ANIMAL", "I-ANIMAL", "L-ANIMAL"]

    evaluated = evaluator.evaluate_sample(sample, prediction)
    evaluation = evaluator.calculate_score([evaluated])

    assert evaluation.pii_precision == 1
    assert evaluation.pii_recall == 1


def test_evaluate_multiple_tokens_partial_match_correct_statistics():
    prediction = ["O", "O", "O", "B-ANIMAL", "L-ANIMAL", "O"]
    model = MockTokensModel(prediction=prediction)
    evaluator = Evaluator(model=model, entities_to_keep=["ANIMAL"])
    sample = InputSample(
        "I am the walrus amaericanus magnifico", masked=None, spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus", "americanus", "magnifico"]
    sample.tags = ["O", "O", "O", "B-ANIMAL", "I-ANIMAL", "L-ANIMAL"]

    evaluated = evaluator.evaluate_sample(sample, prediction)
    evaluation = evaluator.calculate_score([evaluated])

    assert evaluation.pii_precision == 1
    assert evaluation.pii_recall == 4 / 6


def test_evaluate_multiple_tokens_no_match_match_correct_statistics():
    prediction = ["O", "O", "O", "B-SPACESHIP", "L-SPACESHIP", "O"]
    model = MockTokensModel(prediction=prediction)
    evaluator = Evaluator(model=model, entities_to_keep=["ANIMAL"])
    sample = InputSample(
        "I am the walrus amaericanus magnifico", masked=None, spans=None
    )
    sample.tokens = ["I", "am", "the", "walrus", "americanus", "magnifico"]
    sample.tags = ["O", "O", "O", "B-ANIMAL", "I-ANIMAL", "L-ANIMAL"]

    evaluated = evaluator.evaluate_sample(sample, prediction)
    evaluation = evaluator.calculate_score([evaluated])

    assert np.isnan(evaluation.pii_precision)
    assert evaluation.pii_recall == 0


def test_evaluate_multiple_examples_correct_statistics():
    prediction = ["U-PERSON", "O", "O", "U-PERSON", "O", "O"]
    model = MockTokensModel(prediction=prediction)
    evaluator = Evaluator(model=model, entities_to_keep=["PERSON"], skip_words=["-"])
    input_sample = InputSample("My name is Raphael or David", masked=None, spans=None)
    input_sample.tokens = ["My", "name", "is", "Raphael", "or", "David"]
    input_sample.tags = ["O", "O", "O", "U-PERSON", "O", "U-PERSON"]

    evaluated = evaluator.evaluate_all(
        [input_sample, input_sample, input_sample, input_sample]
    )
    scores = evaluator.calculate_score(evaluated)
    assert scores.pii_precision == 0.5
    assert scores.pii_recall == 0.5


def test_evaluate_multiple_examples_ignore_entity_correct_statistics():
    prediction = ["O", "O", "O", "U-PERSON", "O", "U-TENNIS_PLAYER"]
    model = MockTokensModel(prediction=prediction)

    evaluator = Evaluator(model=model, entities_to_keep=["PERSON", "TENNIS_PLAYER"])
    input_sample = InputSample("My name is Raphael or David", masked=None, spans=None)
    input_sample.tokens = ["My", "name", "is", "Raphael", "or", "David"]
    input_sample.tags = ["O", "O", "O", "U-PERSON", "O", "U-PERSON"]

    evaluated = evaluator.evaluate_all(
        [input_sample, input_sample, input_sample, input_sample]
    )
    scores = evaluator.calculate_score(evaluated)
    assert scores.pii_precision == 1
    assert scores.pii_recall == 1


def test_confusion_matrix_correct_metrics():
    from collections import Counter

    evaluated = [
        EvaluationResult(
            results=Counter(
                {
                    ("O", "O"): 150,
                    ("O", "PERSON"): 30,
                    ("O", "COMPANY"): 30,
                    ("PERSON", "PERSON"): 40,
                    ("COMPANY", "COMPANY"): 40,
                    ("PERSON", "COMPANY"): 10,
                    ("COMPANY", "PERSON"): 10,
                    ("PERSON", "O"): 30,
                    ("COMPANY", "O"): 30,
                }
            ),
            model_errors=None,
            text=None,
        )
    ]

    model = MockTokensModel(prediction=None)
    evaluator = Evaluator(model=model, entities_to_keep=["PERSON", "COMPANY"])
    scores = evaluator.calculate_score(evaluated, beta=2.5)

    assert scores.pii_precision == 0.625
    assert scores.pii_recall == 0.625
    assert scores.entity_recall_dict["PERSON"] == 0.5
    assert scores.entity_precision_dict["PERSON"] == 0.5
    assert scores.entity_recall_dict["COMPANY"] == 0.5
    assert scores.entity_precision_dict["COMPANY"] == 0.5


def test_confusion_matrix_2_correct_metrics():
    from collections import Counter

    evaluated = [
        EvaluationResult(
            results=Counter(
                {
                    ("O", "O"): 65467,
                    ("O", "ORG"): 4189,
                    ("GPE", "O"): 3370,
                    ("PERSON", "PERSON"): 2024,
                    ("GPE", "PERSON"): 1488,
                    ("GPE", "GPE"): 1033,
                    ("O", "GPE"): 964,
                    ("ORG", "ORG"): 914,
                    ("O", "PERSON"): 834,
                    ("GPE", "ORG"): 401,
                    ("PERSON", "ORG"): 35,
                    ("PERSON", "O"): 33,
                    ("ORG", "O"): 8,
                    ("PERSON", "GPE"): 5,
                    ("ORG", "PERSON"): 1,
                }
            ),
            model_errors=None,
            text=None,
        )
    ]

    model = MockTokensModel(prediction=None)
    evaluator = Evaluator(model=model)
    scores = evaluator.calculate_score(evaluated, beta=2.5)

    pii_tp = (
        evaluated[0].results[("PERSON", "PERSON")]
        + evaluated[0].results[("ORG", "ORG")]
        + evaluated[0].results[("GPE", "GPE")]
        + evaluated[0].results[("ORG", "GPE")]
        + evaluated[0].results[("ORG", "PERSON")]
        + evaluated[0].results[("GPE", "ORG")]
        + evaluated[0].results[("GPE", "PERSON")]
        + evaluated[0].results[("PERSON", "GPE")]
        + evaluated[0].results[("PERSON", "ORG")]
    )

    pii_fp = (
        evaluated[0].results[("O", "PERSON")]
        + evaluated[0].results[("O", "GPE")]
        + evaluated[0].results[("O", "ORG")]
    )

    pii_fn = (
        evaluated[0].results[("PERSON", "O")]
        + evaluated[0].results[("GPE", "O")]
        + evaluated[0].results[("ORG", "O")]
    )

    assert scores.pii_precision == pii_tp / (pii_tp + pii_fp)
    assert scores.pii_recall == pii_tp / (pii_tp + pii_fn)


def test_dataset_to_metric_identity_model():
    import os

    dir_path = os.path.dirname(os.path.realpath(__file__))
    input_samples = InputSample.read_dataset_json(
        "{}/data/generated_small.json".format(dir_path), length=10
    )

    model = IdentityTokensMockModel()
    evaluator = Evaluator(model=model)
    evaluation_results = evaluator.evaluate_all(input_samples)
    metrics = evaluator.calculate_score(evaluation_results)

    assert metrics.pii_precision == 1
    assert metrics.pii_recall == 1


def test_dataset_to_metric_50_50_model():
    import os

    dir_path = os.path.dirname(os.path.realpath(__file__))
    input_samples = InputSample.read_dataset_json(
        "{}/data/generated_small.json".format(dir_path), length=100
    )

    # Replace 50% of the predictions with a list of "O"
    model = FiftyFiftyIdentityTokensMockModel()
    evaluator = Evaluator(model=model, entities_to_keep=["PERSON"])
    evaluation_results = evaluator.evaluate_all(input_samples)
    metrics = evaluator.calculate_score(evaluation_results)

    print(metrics.pii_precision)
    print(metrics.pii_recall)
    print(metrics.pii_f)

    assert metrics.pii_precision == 1
    assert metrics.pii_recall < 0.75
    assert metrics.pii_recall > 0.25


def test_align_entity_types_correct_output():
    sample1 = InputSample(
        "I live in ABC",
        spans=[Span("A", "a", 0, 1), Span("A", "a", 10, 11), Span("B", "b", 100, 101)],
        create_tags_from_span=False,
    )
    sample2 = InputSample(
        "I live in ABC",
        spans=[Span("A", "a", 0, 1), Span("A", "a", 10, 11), Span("C", "c", 100, 101)],
        create_tags_from_span=False,
    )
    samples = [sample1, sample2]
    mapping = {
        "A": "1",
        "B": "2",
        "C": "1",
    }

    new_samples = Evaluator.align_entity_types(samples, mapping)

    count_per_entity = Counter()
    for sample in new_samples:
        for span in sample.spans:
            count_per_entity[span.entity_type] += 1

    assert count_per_entity["1"] == 5
    assert count_per_entity["2"] == 1


def test_align_entity_types_wrong_mapping_exception():
    sample1 = InputSample(
        "I live in ABC",
        spans=[Span("A", "a", 0, 1), Span("A", "a", 10, 11), Span("B", "b", 100, 101)],
        create_tags_from_span=False,
    )

    entities_mapping = {"Z": "z"}

    with pytest.raises(ValueError):
        Evaluator.align_entity_types(
            input_samples=[sample1], entities_mapping=entities_mapping
        )


@pytest.mark.parametrize(
    "tokens, tags, predicted_tags, precision, recall",
    [
        (
            ["John", "is", "in", "\n", "\t", "London"],
            ["U-PERSON", "O", "O", "B-LOCATION", "I-LOCATION", "I-LOCATION"],
            ["U-PERSON", "O", "O", "O", "O", "B-LOCATION"],
            1,
            1,
        ),
        (
            [">", ">>", ">>>", "Baku"],
            ["O", "O", "O", "U-LOCATION"],
            ["B-LOCATION", "I-LOCATION", "I-LOCATION", "L-LOCATION"],
            1,
            1,
        ),
        (
            ["Mr.", "", "Smith"],
            ["O", "O", "U-PERSON"],
            ["O", "B-PERSON", "I-PERSON"],
            1,
            1,
        ),
        (["!"], ["O"], ["U-PERSON"], np.nan, np.nan),
        ([], [], [], np.nan, np.nan),
    ],
)
def test_skip_words_are_not_counted_as_errors(
    tokens, tags, predicted_tags, precision, recall
):
    model = MockTokensModel(
        prediction=predicted_tags, entities_to_keep=["LOCATION", "PERSON"]
    )

    evaluator = Evaluator(model=model)
    sample = InputSample(full_text=" ".join(tokens), spans=None)
    sample.tokens = tokens
    sample.tags = tags

    evaluated = evaluator.evaluate_sample(sample, predicted_tags)
    final_evaluation = evaluator.calculate_score([evaluated])

    if np.isnan(precision):
        assert np.isnan(final_evaluation.pii_precision)
    else:
        assert final_evaluation.pii_precision == precision

    if np.isnan(recall):
        assert np.isnan(final_evaluation.pii_recall)
    else:
        assert final_evaluation.pii_recall == recall


@pytest.mark.parametrize(
    "tags, predicted_tags, expected_dict",
    [
        (
            ["O", "ID", "SSN"],
            ["O", "SSN", "SSN"],
            {("O", "O"): 1, ("SSN", "SSN"): 2},
        ),
        (
            ["O", "SSN", "SSN"],
            ["O", "ID", "SSN"],
            {("O", "O"): 1, ("SSN", "SSN"): 2},
        ),
        (
            ["O", "MID", "SSN"],
            ["O", "SSN", "SSN"],
            {("O", "O"): 1, ("MID", "SSN"): 1, ("SSN", "SSN"): 1},
        ),
    ],
)
def test_generic_entities_are_treated_like_specific_entities(
    tags, predicted_tags, expected_dict
):
    model = MockTokensModel(prediction=predicted_tags)
    evaluator = Evaluator(model=model)

    tokens = ["A", "123", "456"]

    sample = InputSample(full_text=" ".join(tokens), spans=None)
    sample.tokens = tokens
    sample.tags = tags

    evaluated = evaluator.evaluate_sample(sample, predicted_tags)

    assert evaluated.results == expected_dict


def test_error_type_classification():
    """
    Test that error types are correctly classified:
    - FP: Only when predicting an entity where there should be none (O)
    - FN: When missing an entity (predicting O instead of entity)
    - WrongEntity: When predicting wrong entity type (entity mismatch)
    """
    prediction = ["O", "EMAIL", "PHONE", "LOCATION", "PERSON"]

    evaluator = Evaluator(model=MockTokensModel(prediction))

    # Ground truth: [PERSON, O, EMAIL, PHONE, O]
    # Prediction:   [PERSON, EMAIL, PHONE, LOCATION, PERSON]
    sample = InputSample(
        full_text="John details john@mail.com 123-456-7890 today",
        tokens=["John", "details", "john@mail.com", "123-456-7890", "today"],
        tags=["PERSON", "O", "EMAIL", "PHONE", "O"],
    )


    result = evaluator.evaluate_sample(sample, prediction)

    # Verify error types
    errors = result.model_errors

    # Classify each error
    fps = [e for e in errors if e.error_type == ErrorType.FP]
    fns = [e for e in errors if e.error_type == ErrorType.FN]
    wrong_entities = [e for e in errors if e.error_type == ErrorType.WrongEntity]

    # Should be 2 FPs: "is"->EMAIL and "there"->PERSON
    assert len(fps) == 2
    assert any(e.token == "details" and e.prediction == "EMAIL" for e in fps)
    assert any(e.token == "today" and e.prediction == "PERSON" for e in fps)

    # Should be 1 FNs: Missing PERSON (pun not intended :))
    assert len(fns) == 1
    assert any(e.token == "John" and e.annotation == "PERSON" for e in fns)

    # Should be 2 WrongEntity: PHONE->LOCATION, EMAIL->PHONE
    assert len(wrong_entities) == 2
    assert any(e.token == "john@mail.com"
               and e.annotation == "EMAIL"
               and e.prediction == "PHONE" for e in wrong_entities)
    assert any(e.token == "123-456-7890"
               and e.annotation == "PHONE"
               and e.prediction == "LOCATION" for e in wrong_entities)


def test_results_to_dataframe():
    prediction = ["O", "EMAIL", "PHONE", "LOCATION", "PERSON"]
    tokens = ["John", "details", "john@mail.com", "123-456-7890", "today"]
    tags = ["PERSON", "O", "EMAIL", "PHONE", "O"]
    evaluator = Evaluator(model=MockTokensModel(prediction))

    sample = InputSample(
        full_text="John details john@mail.com 123-456-7890 today",
        tokens=tokens,
        tags=tags
    )

    results = evaluator.evaluate_all([sample, sample])

    df = evaluator.get_results_dataframe(results)
    expected_columns = ["sentence_id", "token", "annotation", "prediction"]
    for col in expected_columns:
        assert col in df.columns

    assert df["annotation"].to_list() == tags + tags
    assert df["prediction"].to_list() == prediction + prediction
    assert df["token"].to_list() == tokens + tokens
    assert df["sentence_id"].to_list() == [0]*len(tokens) + [1]*len(tokens)


def test_score_calculation():
    """
    Test that precision and recall calculations are correct:
    - FP and WrongEntity both hurt precision
    - Only FN hurts recall
    """
    prediction = ["PERSON", "PHONE", "O", "ORGANIZATION"]

    evaluator = Evaluator(model=MockTokensModel(prediction))

    # Ground truth: [PERSON, O, EMAIL]
    # Prediction:   [PERSON, PHONE, LOCATION]
    sample = InputSample(
        full_text="John visited Paris France",
        tokens=["John", "visited", "Paris", "France"],
        tags=["PERSON", "O", "LOCATION", "LOCATION"],
    )

    result = evaluator.evaluate_sample(sample, prediction)
    score = evaluator.calculate_score([result])

    # Expected results:
    # TP: PERSON->PERSON
    # FP: O->PHONE
    # FN: Missing LOCATION
    # WrongEntity: LOCATION->ORGANIZATION

    # Wrong entities are handled differently for PII in general and individual entities

    # PII precision/recall don't take into account wrong entities (treat them as TP)
    # as we are interested in whether PII was detected or not, not the exact type.
    # Precision = (TP + WrongEntity) / (TP + WrongEntity + FP) = (1+1) / (1+1+1) = 0.667
    # Recall = (TP + WrongEntity) / (TP + WrongEntity + FN) = (1+1) / (1+1+1) = 0.667

    assert score.pii_precision == pytest.approx(0.66667 ,2)
    assert score.pii_recall == pytest.approx(0.66667, 2)

    # For individual entities, wrong entities are counted as FPs

    assert score.entity_precision_dict["PERSON"] == 1
    assert np.isnan(score.entity_precision_dict["LOCATION"])
    assert score.entity_precision_dict["PHONE"] == 0
    assert score.entity_precision_dict["ORGANIZATION"] == 0

    assert score.entity_recall_dict["PERSON"] == 1
    assert score.entity_recall_dict["LOCATION"] == 0
    assert np.isnan(score.entity_recall_dict["PHONE"])
    assert np.isnan(score.entity_recall_dict["ORGANIZATION"])


def test_calculate_score_existing_results_counter_indivudal_entities():
    results=Counter(
        {
            ("X", "X"): 50,
            ("Y", "Y"): 60,
            ("Z", "Z"): 70,
            ("X", "O"): 5,
            ("Y", "O"): 6,
            ("Z", "O"): 7,
            ("O", "X"): 5,
            ("O", "Y"): 6,
            ("O", "Z"): 7,
            ("X", "Y"): 5,
            ("X", "Z"): 5,
            ("Y", "X"): 6,
            ("Y", "Z"): 6,
            ("Z", "X"): 7,
            ("Z", "Y"): 7,
        }
    )
    x_tp = sum([results[i] for i in results if i[0] == "X" and i[1] == "X"])
    x_fp_tp = sum([results[i] for i in results if i[1] == "X"])
    x_fn_tp = sum([results[i] for i in results if i[0] == "X"])
    y_tp = sum([results[i] for i in results if i[0] == "Y" and i[1] == "Y"])
    y_fp_tp = sum([results[i] for i in results if i[1] == "Y"])
    y_fn_tp = sum([results[i] for i in results if i[0] == "Y"])
    z_tp = sum([results[i] for i in results if i[0] == "Z" and i[1] == "Z"])
    z_fp_tp = sum([results[i] for i in results if i[1] == "Z"])
    z_fn_tp = sum([results[i] for i in results if i[0] == "Z"])


    expected_x_precision=x_tp/x_fp_tp if x_fp_tp!=0 else np.nan
    expected_x_recall=x_tp/x_fn_tp if x_fn_tp!=0 else np.nan
    expected_y_precision=y_tp/y_fp_tp if y_fp_tp!=0 else np.nan
    expected_y_recall=y_tp/y_fn_tp if y_fn_tp!=0 else np.nan
    expected_z_precision=z_tp/z_fp_tp if z_fp_tp!=0 else np.nan
    expected_z_recall=z_tp/z_fn_tp if z_fn_tp!=0 else np.nan


    evaluator = Evaluator(model=MockTokensModel(prediction=None))
    evaluation_score = evaluator.calculate_score(
        evaluation_results=[EvaluationResult(results)])

    assert evaluation_score.entity_precision_dict["X"] == expected_x_precision
    assert evaluation_score.entity_recall_dict["X"] == expected_x_recall
    assert evaluation_score.entity_precision_dict["Y"] == expected_y_precision
    assert evaluation_score.entity_recall_dict["Y"] == expected_y_recall
    assert evaluation_score.entity_precision_dict["Z"] == expected_z_precision
    assert evaluation_score.entity_recall_dict["Z"] == expected_z_recall
