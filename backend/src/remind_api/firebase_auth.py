import os
from functools import lru_cache

import firebase_admin
from google.auth.exceptions import DefaultCredentialsError
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _firebase_app() -> firebase_admin.App:
    """Initialize the Admin SDK using the deployment's service identity."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        options = {"projectId": project_id} if project_id else None
        try:
            return firebase_admin.initialize_app(options=options)
        except (ValueError, FirebaseError, DefaultCredentialsError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Firebase Authentication is not configured",
            ) from exc


def current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")

    app = _firebase_app()
    try:
        decoded = auth.verify_id_token(credentials.credentials, app=app, check_revoked=True)
    except (auth.InvalidIdTokenError, auth.UserDisabledError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired identity token") from exc
    except FirebaseError as exc:
        raise HTTPException(status_code=503, detail="Firebase token verification is unavailable") from exc

    if decoded.get("email") and not decoded.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email address before continuing")

    return {"uid": decoded["uid"]}
