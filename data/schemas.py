"""Schemas for Saathi's synthetic customer and interaction data."""

from datetime import date as Date

from pydantic import BaseModel, StrictBool


class CustomerRecord(BaseModel):
    customer_id: str
    name: str
    product: str
    tier: str
    city: str
    segment: str
    consent: StrictBool
    agent_id: str
    renewal_date: Date


class InteractionRecord(BaseModel):
    interaction_id: str
    customer_id: str
    date: Date
    channel: str
    text: str
