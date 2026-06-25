from __future__ import annotations

from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, request, session, url_for

from config import load_config

bp = Blueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth()


def init_auth(app) -> None:
    cfg = load_config()
    oauth.init_app(app)
    oauth.register(
        name="entra",
        server_metadata_url=(
            f"https://login.microsoftonline.com/{cfg.oidc_tenant_id}"
            "/v2.0/.well-known/openid-configuration"
        ),
        client_id=cfg.oidc_client_id,
        client_secret=cfg.oidc_client_secret,
        client_kwargs={"scope": "openid email profile"},
    )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def has_valid_token() -> bool:
    """Return True if request carries a valid CLI service token."""
    cfg = load_config()
    if not cfg.cli_token:
        return False
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {cfg.cli_token}"


@bp.get("/login")
def login():
    cfg = load_config()
    return oauth.entra.authorize_redirect(cfg.oidc_redirect_uri)


@bp.get("/callback")
def callback():
    token = oauth.entra.authorize_access_token()
    userinfo = token.get("userinfo") or {}
    session["user"] = {
        "email": userinfo.get("email", ""),
        "name": userinfo.get("name", ""),
    }
    next_url = request.args.get("next") or "/"
    return redirect(next_url)


@bp.get("/logout")
def logout():
    session.clear()
    cfg = load_config()
    tenant = cfg.oidc_tenant_id
    post_logout = request.host_url.rstrip("/")
    return redirect(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={post_logout}"
    )
