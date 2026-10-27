import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from remind_api.db import get_db
from remind_api.firebase_auth import current_identity
from remind_api.models import Account, AuditEvent, CareRelationship, LinkCode, PatientProfile
from remind_api.schemas import AccountCreate, AccountView, LinkCodeRedeem, LinkCodeView, PatientCreate, PatientView

router = APIRouter(prefix="/v1")
LINK_CODE_TTL_SECONDS = 15 * 60


def account_for(identity: dict[str, str], db: Session) -> Account:
    account = db.get(Account, identity["uid"])
    if account is None:
        raise HTTPException(status_code=403, detail="Create an account profile before using ReMind")
    return account


def require_role(account: Account, role: str) -> None:
    if account.role != role:
        raise HTTPException(status_code=403, detail=f"This action requires a {role} account")


def audit(db: Session, actor_uid: str, action: str, resource_id: str) -> None:
    db.add(AuditEvent(actor_uid=actor_uid, action=action, resource_id=resource_id))


@router.post("/account", response_model=AccountView, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    identity: dict[str, str] = Depends(current_identity),
    db: Session = Depends(get_db),
):
    if db.get(Account, identity["uid"]):
        raise HTTPException(status_code=409, detail="Account profile already exists")
    name = payload.display_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Display name must not be blank")
    account = Account(firebase_uid=identity["uid"], role=payload.role, display_name=name)
    db.add(account)
    audit(db, account.firebase_uid, "account.created", account.firebase_uid)
    db.commit()
    db.refresh(account)
    return account


@router.get("/account", response_model=AccountView)
def get_account(identity: dict[str, str] = Depends(current_identity), db: Session = Depends(get_db)):
    return account_for(identity, db)


@router.post("/patients", response_model=PatientView, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    identity: dict[str, str] = Depends(current_identity),
    db: Session = Depends(get_db),
):
    caregiver = account_for(identity, db)
    require_role(caregiver, "caregiver")
    name = payload.display_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Display name must not be blank")
    patient = PatientProfile(display_name=name, created_by_uid=caregiver.firebase_uid)
    db.add(patient)
    db.flush()
    db.add(CareRelationship(caregiver_uid=caregiver.firebase_uid, patient_id=patient.id))
    audit(db, caregiver.firebase_uid, "patient.created", patient.id)
    db.commit()
    db.refresh(patient)
    return PatientView(id=patient.id, display_name=patient.display_name, linked=False,
                       relationship_id=db.scalar(select(CareRelationship.id).where(
                           CareRelationship.patient_id == patient.id,
                           CareRelationship.caregiver_uid == caregiver.firebase_uid)))


@router.get("/patients", response_model=list[PatientView])
def list_patients(identity: dict[str, str] = Depends(current_identity), db: Session = Depends(get_db)):
    account = account_for(identity, db)
    if account.role == "caregiver":
        rows = db.execute(
            select(PatientProfile, CareRelationship)
            .join(CareRelationship, CareRelationship.patient_id == PatientProfile.id)
            .where(CareRelationship.caregiver_uid == account.firebase_uid, CareRelationship.status == "active")
        ).all()
        return [PatientView(id=p.id, display_name=p.display_name, linked=p.patient_uid is not None,
                            relationship_id=rel.id) for p, rel in rows]
    profile = db.scalar(select(PatientProfile).where(PatientProfile.patient_uid == account.firebase_uid))
    return [] if profile is None else [PatientView(id=profile.id, display_name=profile.display_name, linked=True)]


@router.post("/patients/{patient_id}/link-codes", response_model=LinkCodeView, status_code=status.HTTP_201_CREATED)
def create_link_code(
    patient_id: str,
    identity: dict[str, str] = Depends(current_identity),
    db: Session = Depends(get_db),
):
    caregiver = account_for(identity, db)
    require_role(caregiver, "caregiver")
    relationship = db.scalar(
        select(CareRelationship).where(
            CareRelationship.patient_id == patient_id,
            CareRelationship.caregiver_uid == caregiver.firebase_uid,
            CareRelationship.status == "active",
        )
    )
    patient = db.get(PatientProfile, patient_id)
    if relationship is None or patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    if patient.patient_uid is not None:
        raise HTTPException(status_code=409, detail="Patient profile is already linked")
    raw_code = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=LINK_CODE_TTL_SECONDS)
    db.add(LinkCode(patient_id=patient_id, created_by_uid=caregiver.firebase_uid,
                    token_hash=hashlib.sha256(raw_code.encode()).hexdigest(), expires_at=expires_at))
    audit(db, caregiver.firebase_uid, "link_code.issued", patient_id)
    db.commit()
    return LinkCodeView(code=raw_code, expires_in_seconds=LINK_CODE_TTL_SECONDS)


@router.post("/link-codes/redeem", response_model=PatientView)
def redeem_link_code(
    payload: LinkCodeRedeem,
    identity: dict[str, str] = Depends(current_identity),
    db: Session = Depends(get_db),
):
    patient_account = account_for(identity, db)
    require_role(patient_account, "patient")
    token_hash = hashlib.sha256(payload.code.strip().encode()).hexdigest()
    link_code = db.scalar(select(LinkCode).where(LinkCode.token_hash == token_hash).with_for_update())
    now = datetime.now(timezone.utc)
    if link_code is None or link_code.used_at is not None:
        raise HTTPException(status_code=400, detail="Link code is invalid or already used")
    expires_at = link_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=400, detail="Link code has expired")
    profile = db.get(PatientProfile, link_code.patient_id)
    if profile is None or profile.patient_uid is not None:
        raise HTTPException(status_code=409, detail="Patient profile is already linked or unavailable")
    profile.patient_uid = patient_account.firebase_uid
    link_code.used_at = now
    audit(db, patient_account.firebase_uid, "patient.linked", profile.id)
    db.commit()
    return PatientView(id=profile.id, display_name=profile.display_name, linked=True)


@router.post("/relationships/{relationship_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_relationship(
    relationship_id: str,
    identity: dict[str, str] = Depends(current_identity),
    db: Session = Depends(get_db),
):
    caregiver = account_for(identity, db)
    require_role(caregiver, "caregiver")
    relationship = db.scalar(
        select(CareRelationship).where(
            CareRelationship.id == relationship_id,
            CareRelationship.caregiver_uid == caregiver.firebase_uid,
            CareRelationship.status == "active",
        )
    )
    if relationship is None:
        raise HTTPException(status_code=404, detail="Active relationship not found")
    relationship.status = "revoked"
    relationship.revoked_at = datetime.now(timezone.utc)
    audit(db, caregiver.firebase_uid, "relationship.revoked", relationship.patient_id)
    db.commit()
