"""Radar explanations and per-customer sentiment for the UI (synthetic data)."""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import joblib

from app.services.insights import customer_sentiment, radar_details
from ml.radar import FEATURES


def test_radar_details_give_values_and_signed_contributions(tmp_path):
    train = pd.DataFrame({'days_to_renewal':[30,-5,10,-20],'interaction_count_90d':[1,4,2,5],
                          'sentiment_score':[0.5,-0.6,0.1,-0.8],'annual_premium_inr':[10000,20000,15000,30000]})
    model = make_pipeline(StandardScaler(), LogisticRegression()).fit(train[FEATURES], [0,1,0,1])
    joblib.dump(model, tmp_path / 'm.joblib')
    frame = train.assign(customer_id=['A','B','C','D'])
    d = radar_details(frame, tmp_path / 'm.joblib')
    assert [f['feature'] for f in d['B']] == FEATURES
    assert d['B'][2]['value'] == -0.6 and d['B'][2]['contribution'] is not None


def test_radar_details_without_a_model_still_show_values(tmp_path):
    frame = pd.DataFrame([{'customer_id':'A','days_to_renewal':5,'interaction_count_90d':1,
                           'sentiment_score':0.1,'annual_premium_inr':9000.0}])
    d = radar_details(frame, tmp_path / 'missing.joblib')
    assert d['A'][0]['value'] == 5 and d['A'][0]['contribution'] is None


def test_customer_sentiment_joins_text_labels_and_score():
    s = customer_sentiment('C-204')
    assert s['sentiment_score_90d'] is not None
    assert s['interactions'] and all(i['sentiment'] in ('positive','neutral','negative','mixed') for i in s['interactions'])
    assert all(i['text'] for i in s['interactions'])
    assert customer_sentiment('C-NOPE')['interactions'] == []
