import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from remind_api import models
from remind_api.db import Base
from remind_api.routes import (
    create_account,
    create_link_code,
    create_patient,
    list_patients,
    redeem_link_code,
    revoke_relationship,
)
from remind_api.schemas import AccountCreate, LinkCodeRedeem, PatientCreate


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_caregiver_patient_link_code_is_single_use(db):
    caregiver_id = {"uid": "caregiver-test"}
    create_account(AccountCreate(role="caregiver", display_name="Alex"), caregiver_id, db)
    patient = create_patient(PatientCreate(display_name="Sam"), caregiver_id, db)
    link = create_link_code(patient.id, caregiver_id, db)
    token_hash = hashlib.sha256(link.code.encode()).hexdigest()
    stored_code = db.scalar(select(models.LinkCode).where(models.LinkCode.token_hash == token_hash))
    assert stored_code.token_hash != link.code

    patient_id = {"uid": "patient-test"}
    create_account(AccountCreate(role="patient", display_name="Sam"), patient_id, db)
    linked = redeem_link_code(LinkCodeRedeem(code=link.code), patient_id, db)
    assert linked.id == patient.id
    assert linked.linked is True

    with pytest.raises(HTTPException) as replay:
        redeem_link_code(LinkCodeRedeem(code=link.code), patient_id, db)
    assert replay.value.status_code == 400


def test_link_code_expires(db):
    caregiver_id = {"uid": "caregiver-test"}
    create_account(AccountCreate(role="caregiver", display_name="Alex"), caregiver_id, db)
    patient = create_patient(PatientCreate(display_name="Sam"), caregiver_id, db)
    link = create_link_code(patient.id, caregiver_id, db)
    token_hash = hashlib.sha256(link.code.encode()).hexdigest()
    stored = db.scalar(select(models.LinkCode).where(models.LinkCode.token_hash == token_hash))
    stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    patient_id = {"uid": "patient-test"}
    create_account(AccountCreate(role="patient", display_name="Sam"), patient_id, db)
    with pytest.raises(HTTPException) as expired:
        redeem_link_code(LinkCodeRedeem(code=link.code), patient_id, db)
    assert expired.value.status_code == 400


def test_patient_cannot_create_patient_profile(db):
    patient_id = {"uid": "patient-test"}
    create_account(AccountCreate(role="patient", display_name="Sam"), patient_id, db)
    with pytest.raises(HTTPException) as denied:
        create_patient(PatientCreate(display_name="Other"), patient_id, db)
    assert denied.value.status_code == 403


def test_relationship_revocation_removes_caregiver_access(db):
    caregiver_id = {"uid": "caregiver-test"}
    create_account(AccountCreate(role="caregiver", display_name="Alex"), caregiver_id, db)
    patient = create_patient(PatientCreate(display_name="Sam"), caregiver_id, db)
    assert len(list_patients(caregiver_id, db)) == 1

    revoke_relationship(patient.relationship_id, caregiver_id, db)
    assert list_patients(caregiver_id, db) == []
    with pytest.raises(HTTPException) as denied:
        create_link_code(patient.id, caregiver_id, db)
    assert denied.value.status_code == 404


def test_account_role_cannot_be_changed(db):
    caregiver_id = {"uid": "caregiver-test"}
    create_account(AccountCreate(role="caregiver", display_name="Alex"), caregiver_id, db)
    with pytest.raises(HTTPException) as duplicate:
        create_account(AccountCreate(role="patient", display_name="Alex"), caregiver_id, db)
    assert duplicate.value.status_code == 409
