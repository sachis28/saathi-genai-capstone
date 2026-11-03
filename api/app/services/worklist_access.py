"""Fail-closed access gate for the CRM-linked Radar worklist.

The local bearer adapter is replaceable by the application's identity provider.
No request header or query parameter may directly select an agent identity.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
import pandera.pandas as pa
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, ValidationError

from data.validate import validate_radar_inference
from ml.common import ROOT
from app.services.customers import policy_metadata, reference_date
from datetime import date


class AgentPrincipal(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    agent_id: StrictStr = Field(min_length=1)
    allowed_products: tuple[StrictStr, ...] = Field(min_length=1)


class AgentCredential(AgentPrincipal):
    token_sha256: StrictStr = Field(pattern=r'^[a-f0-9]{64}$')


class CustomerAccess(BaseModel):
    # Existing CRM fields are retained upstream; only access metadata is read here.
    model_config = ConfigDict(extra='ignore')
    customer_id: StrictStr = Field(min_length=1)
    agent_id: StrictStr | None = None
    product: StrictStr | None = None
    consent: StrictBool | None = None
    renewal_date: date | None = None
    cancelled: StrictBool = False
    policy_status: Literal['ACTIVE', 'IN_GRACE', 'LAPSED', 'CANCELLED'] | None = None
    renewal_eligible: StrictBool | None = None


bearer = HTTPBearer(auto_error=False)


def _read_json(path: Path):
    # Reject duplicate JSON keys instead of silently trusting the final value.
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_keys)


def authenticate_agent(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AgentPrincipal:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Agent authentication required',
                            headers={'WWW-Authenticate': 'Bearer'})
    configured = os.getenv('SAATHI_AGENT_CREDENTIALS_FILE')
    try:
        if not configured:
            raise ValueError('No credential store configured')
        records = _read_json(Path(configured))
        if not isinstance(records, list) or not records:
            raise ValueError('Invalid credential store')
        agents = [AgentCredential.model_validate(row) for row in records]
        if len({a.token_sha256 for a in agents}) != len(agents):
            raise ValueError('Duplicate credential digest')
    except (OSError, ValueError, TypeError, ValidationError):
        raise HTTPException(status_code=503, detail='Agent authentication is not configured')
    digest = hashlib.sha256(credentials.credentials.encode('utf-8')).hexdigest()
    matches = [agent for agent in agents if hmac.compare_digest(agent.token_sha256, digest)]
    if not matches:
        raise HTTPException(status_code=401, detail='Invalid agent credentials',
                            headers={'WWW-Authenticate': 'Bearer'})
    agent = matches[0]
    return AgentPrincipal(agent_id=agent.agent_id, allowed_products=agent.allowed_products)


def filter_radar_rows(frame: pd.DataFrame, customers: list, principal: AgentPrincipal) -> pd.DataFrame:
    """Apply authoritative CRM access rules before any local or cloud inference.

    Missing policy metadata excludes a row. Malformed/unknown metadata rejects the
    request, rather than assigning an inferred status. Overdue days are untouched.
    """
    try:
        valid = validate_radar_inference(frame.copy())
    except (pa.errors.SchemaError, pa.errors.SchemaErrors) as error:
        raise ValueError('Invalid Radar feature contract') from error
    if not isinstance(customers, list):
        raise ValueError('Expected CRM customer records')
    records = [CustomerAccess.model_validate({**row, **policy_metadata(row)}) for row in customers]
    by_id = {c.customer_id: c for c in records}
    if len(by_id) != len(records):
        raise ValueError('Duplicate CRM customer ID')
    permitted = {
        c.customer_id for c in records
        if c.agent_id == principal.agent_id
        and c.product in principal.allowed_products
        and c.renewal_eligible is True
        and c.policy_status in ('ACTIVE', 'IN_GRACE')
    }
    # Visibility is independent of consent; consent is enforced before outbound send.
    # Check the pinned feature snapshot against the central renewal-date calculation.
    selected = valid.loc[valid.customer_id.isin(permitted)].copy()
    for row in selected.itertuples():
        customer = by_id[row.customer_id]
        if row.days_to_renewal != (customer.renewal_date - reference_date()).days:
            raise ValueError("Radar/CRM reference-date mismatch")
    return selected


def load_authorized_radar_frame(principal: AgentPrincipal) -> pd.DataFrame:
    features_path = Path(os.getenv('RADAR_INPUT_FILE') or str(ROOT / 'data/radar_input.json'))
    customers_path = Path(os.getenv('RADAR_CUSTOMERS_FILE') or str(ROOT / 'data/customers.json'))
    features = _read_json(features_path)
    customers = _read_json(customers_path)
    if not isinstance(features, list) or not features:
        raise ValueError('Expected nonempty CRM-linked Radar rows')
    if isinstance(customers, dict):
        customers = customers.get('customers')
    return filter_radar_rows(pd.DataFrame(features), customers, principal)
