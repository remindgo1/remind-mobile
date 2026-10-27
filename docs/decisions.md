# Initial engineering decisions

Status: proposed defaults for project initialization, pending team confirmation.

| Topic | Starting point | Decision still needed |
|---|---|---|
| Mobile app | React Native with Expo | Configure EAS project and Firebase app |
| API | Python 3.12+ / FastAPI on Google Cloud Run | Configure Google Cloud project and service identity |
| Identity | Firebase Authentication in the app; Firebase Admin SDK verifies ID tokens in the API | Configure Firebase DEV/TEST projects and sign-in providers |
| Database | PostgreSQL for shared environments | Provision isolated DEV and TEST database instances; set backup/retention policy |
| Environments | DEV and TEST only for Phase 1; no PROD release in this slice | Configure GitHub OIDC, Cloud Run, Cloud SQL, and EAS secrets |
| Patient access | Separate identity and patient profile; explicit caregiver relationship | Define assisted onboarding and consent/revocation workflow |

## Security boundaries

- Authentication proves the caller's identity; it does not grant access to a patient.
- Patient access is authorized through an active caregiver–patient relationship and its explicit permissions.
- Patient IDs and linking codes are identifiers, not durable secrets or authorization substitutes.
- Linking codes must be short-lived, single-use, securely generated, and stored as hashes.
- Sensitive access and relationship changes need auditable events.
- Do not store production data or credentials in development environments.

## Authentication flow

1. React Native signs the user in through Firebase Authentication.
2. The app sends the Firebase ID token as a Bearer token over HTTPS when calling the API.
3. The API verifies token signature, issuer, audience, and expiry with Firebase Admin SDK and uses the verified Firebase UID as the caller identity.
4. The API separately checks the caller's role and active caregiver–patient relationship permissions for each patient-data request.

Firebase authentication establishes identity only. The API must not trust a UID or role supplied in a request body. Keep Admin credentials out of the mobile app; use Application Default Credentials in Google-hosted environments or a securely managed service identity elsewhere.

## Phase 1 release scope

Phase 1 provides Firebase email/password sign-in, a one-time immutable role/profile, caregiver patient-profile creation, 15-minute single-use linking codes, patient account linking, relationship revocation, audit events, and a minimal React Native flow. DEV and TEST are separate deployments with separate Firebase projects, databases, and credentials. Later product phases follow the same incremental delivery pipeline after Phase 1 is reviewed.

Consent and representative authorization must be agreed with the team before real patient onboarding. The current linking-code flow is a development workflow and is not a substitute for that policy.
