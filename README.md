# ReMind

ReMind is an assistive-care platform for memory recall, daily routines, and caregiver coordination. It is intended to support daily functioning and does not diagnose, treat, prevent, or cure medical conditions.

## Development status

The repository is at project initialization. The first delivery target is authentication, patient profiles, and authorized caregiver–patient linking. The product approach document is planning input; its internal request for team agreement is not treated as an instruction to the development agent.

## Stack

- Mobile app: React Native with Expo/EAS
- Backend: Python 3.12+ and FastAPI
- Authentication: Firebase Authentication in the app; Firebase Admin SDK verifies ID tokens in the API
- Database: PostgreSQL for shared environments; local development may use an isolated local database

Firebase projects, sign-in providers, patient onboarding/consent decisions, and deployment secrets still need configuration. The initial pipeline targets Google Cloud Run and Expo EAS for DEV and TEST only.

## Milestone 1

1. Configure separate Firebase Authentication projects for DEV and TEST.
2. Apply database migrations and create caregiver/patient account profiles.
3. Create patient profiles and issue short-lived, single-use linking codes.
4. Redeem a code from a patient account and revoke caregiver relationships.
5. Exercise authorization, linking, and expiry behavior in CI and TEST.

Use synthetic data in development and staging. A patient identifier is never an authorization credential. Every patient-data request must be checked against the authenticated identity and active relationship permissions.

## Repository layout

```text
backend/       FastAPI service
mobile/        React Native app (scaffold to follow)
docs/          product and engineering decisions
```

## Run locally

1. Copy `backend/.env.example` to `backend/.env` and `mobile/.env.example` to `mobile/.env`; fill in a Firebase DEV project and the API URL.
2. Start the local PostgreSQL database with `docker compose up -d postgres`.
3. In `backend`, install `.[dev]`, set `DATABASE_URL` to the local PostgreSQL URL, run `alembic upgrade head`, then start `uvicorn remind_api.main:app --reload`.
4. In `mobile`, run `npm ci` then `npm start`.

The API uses Google Application Default Credentials for Firebase Admin. For local development, authenticate with the Google Cloud CLI for the configured Firebase project. Never put an Admin service-account key in the app or commit one to this repository.

## DEV/TEST delivery

Push to `dev` or `test` to run CI and deploy that environment. GitHub Actions uses Workload Identity Federation to deploy the API to Cloud Run and EAS to create an internal installable app build. Configure the `dev` and `test` GitHub Environments independently before enabling deployment. See [deployment setup](docs/deployment.md).

Phase 1 currently covers account/profile setup, patient profile creation, caregiver–patient linking, and relationship revocation. Real patient onboarding requires a team-approved consent and representative-authorization process before use with real data.
