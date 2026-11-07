import pickle

import pytest
from pydantic import ValidationError

from poptimizer.core import domain
from poptimizer.data.features import features
from poptimizer.evolve.dl import datasets, training
from poptimizer.evolve.models import evolve


def _ticker_data() -> datasets.TickerData:
    returns = features.NumFeat.RETURNS
    num_feat = [
        {returns: 0.01, features.NumFeat.CLOSE: 100.0},
        {returns: 0.02, features.NumFeat.CLOSE: 101.0},
        {returns: -0.01, features.NumFeat.CLOSE: 100.0},
        {returns: 0.03, features.NumFeat.CLOSE: 103.0},
        {returns: 0.01, features.NumFeat.CLOSE: 104.0},
    ]

    return datasets.TickerData(
        ticker=domain.Ticker("TEST"),
        days=datasets.Days(history=2, forecast=1, test=2),
        num_feat=num_feat,
        num_feat_selected=[features.NumFeat.CLOSE],
        emb_feat=[1],
        emb_seq_feat=[[1]],
        lag_feat=False,
    )


def _job() -> training.TrainingJob:
    model = evolve.Model(uid=evolve.random_model_uid())
    evolution = evolve.Evolution(uid=evolve.random_model_uid())

    return training.TrainingJob(model=model, evolution=evolution)


def test_job_and_result_are_frozen():
    job = _job()
    result = training.TrainingResult(
        forecast=training.Forecast(mean=[[0.01]], cov=[[0.0004]]),
        duration=1.5,
        test=evolve.TestResults(llh=[0.5], alfa=0.01, ret=0.02),
    )

    with pytest.raises(ValidationError):
        job.evolution = evolve.Evolution()  # type: ignore[misc]
    with pytest.raises(ValidationError):
        result.duration = 2.0  # type: ignore[misc]
    with pytest.raises(ValidationError):
        result.forecast = training.Forecast(mean=[[0.02]], cov=[[0.0004]])  # type: ignore[misc]


def test_job_pickle_round_trip():
    job = _job()

    restored = pickle.loads(pickle.dumps(job))

    assert restored == job


def test_data_pickle_round_trip():
    data = training.TrainingData(
        tickers_data=[_ticker_data()],
        emb_size=[3],
        emb_seq_size=[2],
    )

    restored = pickle.loads(pickle.dumps(data))

    assert len(restored.tickers_data) == 1
    assert restored.emb_size == [3]
    assert restored.emb_seq_size == [2]


def test_result_pickle_round_trip():
    result = training.TrainingResult(
        forecast=training.Forecast(mean=[[0.01], [0.02]], cov=[[0.0004, 0.0001], [0.0001, 0.0009]]),
        duration=1.5,
        test=evolve.TestResults(llh=[0.5, 0.6], alfa=0.01, ret=0.02),
    )

    restored = pickle.loads(pickle.dumps(result))

    assert restored == result
