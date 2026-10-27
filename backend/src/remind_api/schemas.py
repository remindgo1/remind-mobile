from pydantic import BaseModel, ConfigDict, Field


class AccountCreate(BaseModel):
    role: str = Field(pattern="^(caregiver|patient)$")
    display_name: str = Field(min_length=1, max_length=120)


class AccountView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    firebase_uid: str
    role: str
    display_name: str


class PatientCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


class PatientView(BaseModel):
    id: str
    display_name: str
    linked: bool
    relationship_id: str | None = None


class LinkCodeView(BaseModel):
    code: str
    expires_in_seconds: int


class LinkCodeRedeem(BaseModel):
    code: str = Field(min_length=20, max_length=128)
