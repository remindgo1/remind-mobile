# DEV and TEST deployment setup

The workflows deploy only the `dev` and `test` branches. A successful Phase 1 CI run is required by the pipeline before release. Set up the infrastructure and credentials below before pushing to either deployment branch.

## Google Cloud

Create one Cloud Run service and one Cloud SQL PostgreSQL database per environment. Create a dedicated Cloud Run runtime service account for each environment and grant it Firebase Authentication token verification access for that environment's Firebase project, plus access to the environment's `DATABASE_URL` secret. Configure Cloud Run with the corresponding Cloud SQL instance.

Configure GitHub Workload Identity Federation for the repository and grant the deployment service account the narrow Cloud Run deploy, Cloud Build, Artifact Registry, Service Account User, and Secret Manager permissions needed by the workflow. Restrict the provider condition to this repository and the `dev` and `test` GitHub Environments.

Create a Secret Manager secret named `DATABASE_URL` separately in each GCP project. It must contain a PostgreSQL SQLAlchemy URL for that environment's Cloud SQL instance. The Cloud Run runtime service account needs permission to access this secret.

## GitHub Environments

Create GitHub Environments named exactly `dev` and `test`. Add these environment variables to each:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`
- `CLOUD_SQL_INSTANCE` (Cloud SQL connection name)
- `FIREBASE_PROJECT_ID`
- `EAS_PROJECT_ID`
- `EXPO_PUBLIC_API_BASE_URL` (the HTTPS URL for that environment's Cloud Run service)
- `EXPO_PUBLIC_FIREBASE_API_KEY`
- `EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN`
- `EXPO_PUBLIC_FIREBASE_APP_ID`

Add the EAS access token as an environment secret named `EXPO_TOKEN`. The GCP deployment workflow authenticates with OIDC, not a stored service-account key. Ensure the EAS project is initialized and that its project ID matches the environment variable.

Enable Firebase email/password sign-in separately in the DEV and TEST Firebase projects and register the Expo app configuration. Use synthetic accounts and data in TEST. Keep all Firebase, database, and Cloud Run settings separate between environments.

## Branch flow

- `dev`: deploy API and internal app build to DEV after CI passes.
- `test`: deploy API and internal app build to TEST after CI passes.
- Production deployment is deliberately outside Phase 1.

The test deployment's `EXPO_PUBLIC_API_BASE_URL` must point at the service deployed for TEST. Firebase configuration values are public client config; Admin credentials and database credentials remain server-side secrets.
