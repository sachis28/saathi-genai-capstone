"""Synthetic access decisions only; no real agent credentials or CRM statuses."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.services.worklist_access import (
    AgentPrincipal, authenticate_agent, filter_radar_rows, load_authorized_radar_frame,
)

@pytest.fixture(autouse=True)
def fixed_date(monkeypatch):
    monkeypatch.setenv('SAATHI_AS_OF_DATE','2026-10-28')


TEST_TOKEN = 'synthetic-test-token-not-a-real-credential'


@pytest.fixture
def principal():
    return AgentPrincipal(agent_id='A-001', allowed_products=('Health',))


@pytest.fixture
def frame():
    return pd.DataFrame([
        {'customer_id':'DEMO-OVERDUE','days_to_renewal':-5,'interaction_count_90d':3,
         'sentiment_score':-0.29,'annual_premium_inr':11937.33,'consent':True},
        {'customer_id':'DEMO-ACTIVE','days_to_renewal':15,'interaction_count_90d':3,
         'sentiment_score':0.05,'annual_premium_inr':32331.91,'consent':True},
    ])


@pytest.fixture
def customers():
    return [
        {'customer_id':'DEMO-OVERDUE','agent_id':'A-001','product':'Health','consent':True,
         'renewal_date':'2026-10-23'},
        {'customer_id':'DEMO-ACTIVE','agent_id':'A-001','product':'Health','consent':True,
         'renewal_date':'2026-11-12'},
    ]


def test_authorized_expired_policy_keeps_signed_days(frame, customers, principal):
    result = filter_radar_rows(frame, customers, principal)
    pd.testing.assert_frame_equal(result, frame)
    assert result.iloc[0].days_to_renewal == -5


@pytest.mark.parametrize('change', [
    {'cancelled':True}, {'renewal_date':'2026-09-27'}, {'renewal_date':None},
    {'agent_id':'OTHER-AGENT'}, {'agent_id':None}, {'product':'Motor'}, {'product':None},
])
def test_exclude_without_all_access_conditions(frame, customers, principal, change):
    customers[0].update(change)
    assert filter_radar_rows(frame, customers, principal).customer_id.tolist() == ['DEMO-ACTIVE']


def test_no_consent_stays_visible(frame,customers,principal):
    frame.loc[0,'consent'] = False
    customers[0]['consent'] = False
    assert len(filter_radar_rows(frame,customers,principal)) == 2


def test_date_mismatch_rejected(frame,customers,principal):
    frame.loc[0,'days_to_renewal'] = -4
    with pytest.raises(ValueError,match='reference-date'): filter_radar_rows(frame,customers,principal)


@pytest.mark.parametrize('change', [{'cancelled':'true'},{'policy_status':'unknown'},{'consent':'false'}])
def test_malformed_access_metadata_rejected(frame,customers,principal,change):
    customers[0].update(change)
    with pytest.raises(ValueError): filter_radar_rows(frame,customers,principal)


def test_duplicate_crm_and_bad_features_rejected(frame, customers, principal):
    with pytest.raises(ValueError, match='Duplicate'):
        filter_radar_rows(frame, customers+[customers[0]], principal)
    frame.loc[0,'sentiment_score'] = float('nan')
    with pytest.raises(ValueError, match='feature contract'):
        filter_radar_rows(frame, customers, principal)


def test_credential_store_authenticates_scopes_and_rereads_revocation(tmp_path, monkeypatch):
    path = tmp_path / 'credentials.json'
    record = {'agent_id':'A-001','allowed_products':['Health'],
              'token_sha256':hashlib.sha256(TEST_TOKEN.encode()).hexdigest()}
    path.write_text(json.dumps([record]))
    monkeypatch.setenv('SAATHI_AGENT_CREDENTIALS_FILE',str(path))
    credential = HTTPAuthorizationCredentials(scheme='Bearer', credentials=TEST_TOKEN)
    principal = authenticate_agent(credential)
    assert principal.agent_id == 'A-001' and principal.allowed_products == ('Health',)
    with pytest.raises(HTTPException) as e:
        authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer',credentials='wrong'))
    assert e.value.status_code == 401
    path.write_text(json.dumps([{**record,'token_sha256':'0'*64}]))
    with pytest.raises(HTTPException) as e: authenticate_agent(credential)
    assert e.value.status_code == 401


def test_no_credentials_or_missing_configuration_rejected(monkeypatch):
    with pytest.raises(HTTPException) as e: authenticate_agent(None)
    assert e.value.status_code == 401
    monkeypatch.delenv('SAATHI_AGENT_CREDENTIALS_FILE',raising=False)
    with pytest.raises(HTTPException) as e:
        authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer', credentials=TEST_TOKEN))
    assert e.value.status_code == 503


@pytest.mark.parametrize('records', [[], {}, [{'agent_id':'A-001','allowed_products':[], 'token_sha256':'x'}]])
def test_bad_credential_store_fails_closed(tmp_path,monkeypatch,records):
    path = tmp_path / 'credentials.json'
    path.write_text(json.dumps(records))
    monkeypatch.setenv('SAATHI_AGENT_CREDENTIALS_FILE',str(path))
    with pytest.raises(HTTPException) as e:
        authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer', credentials=TEST_TOKEN))
    assert e.value.status_code == 503


def test_load_crm_input_not_training_rows(tmp_path, monkeypatch, frame, customers, principal):
    source = tmp_path / 'input.json'
    crm = tmp_path / 'customers.json'
    source.write_text(frame.to_json(orient='records'))
    crm.write_text(json.dumps(customers))
    monkeypatch.setenv('RADAR_INPUT_FILE',str(source))
    monkeypatch.setenv('RADAR_CUSTOMERS_FILE',str(crm))
    result = load_authorized_radar_frame(principal)
    assert result.customer_id.tolist() == ['DEMO-OVERDUE','DEMO-ACTIVE']
    assert list(result.columns) == list(frame.columns)
    assert 'policy_status' not in result and 'agent_id' not in result
    crm.write_text('[{"customer_id":"one","customer_id":"two"}]')
    with pytest.raises(ValueError,match='Duplicate JSON'): load_authorized_radar_frame(principal)


def test_inline_credential_store_authenticates(monkeypatch):
    monkeypatch.delenv('SAATHI_AGENT_CREDENTIALS_FILE', raising=False)
    store = [{'agent_id':'A-001','allowed_products':['Health'],
              'token_sha256':hashlib.sha256(TEST_TOKEN.encode()).hexdigest()}]
    monkeypatch.setenv('SAATHI_AGENT_CREDENTIALS', json.dumps(store))
    agent = authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer', credentials=TEST_TOKEN))
    assert agent.agent_id == 'A-001'
    with pytest.raises(HTTPException) as denied:
        authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer', credentials='wrong'))
    assert denied.value.status_code == 401


def test_no_credential_store_fails_closed(monkeypatch):
    monkeypatch.delenv('SAATHI_AGENT_CREDENTIALS_FILE', raising=False)
    monkeypatch.delenv('SAATHI_AGENT_CREDENTIALS', raising=False)
    with pytest.raises(HTTPException) as e:
        authenticate_agent(HTTPAuthorizationCredentials(scheme='Bearer', credentials=TEST_TOKEN))
    assert e.value.status_code == 503
