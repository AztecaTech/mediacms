"""
LTI 1.3 tool-side OIDC login initiation and id_token validation.

Spec: IMS Security for LTI 1.3. NRPS, Deep Linking, and AGS are not implemented here.
"""

import secrets
from urllib.parse import quote, urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.lti_jwt import LtiClaimsExtractor, LtiIdTokenValidationError, LtiIdTokenVerifier
from learning.methods.lti_launch_resolution import (
    LtiCourseSlugResolver,
    LtiResourceLinkPersistenceManager,
)


def _lti_platforms():
    raw = getattr(settings, "LMS_LTI_PLATFORMS", [])
    if not isinstance(raw, list):
        return []
    return raw


def _find_platform(issuer: str):
    for row in _lti_platforms():
        if not isinstance(row, dict):
            continue
        if (row.get("issuer") or "").strip() == (issuer or "").strip():
            return row
    return None


def _jwt_leeway():
    return int(getattr(settings, "LMS_LTI_JWT_LEEWAY_SECONDS", 60))


class LtiOidcLoginInitiationView(APIView):
    """Platform redirects the browser here (GET or POST) to start the tool login."""

    permission_classes = [AllowAny]
    parser_classes = [FormParser, MultiPartParser]

    def _params(self, request):
        if request.method == "POST":
            return request.POST
        return request.GET

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        p = self._params(request)
        iss = (p.get("iss") or "").strip()
        client_id = (p.get("client_id") or "").strip()
        login_hint = (p.get("login_hint") or "").strip()
        target_link_uri = (p.get("target_link_uri") or "").strip()
        lti_message_hint = p.get("lti_message_hint") or ""
        deployment_id = (p.get("lti_deployment_id") or p.get("deployment_id") or "").strip()

        if not iss or not client_id or not login_hint or not target_link_uri:
            return Response(
                {"detail": "Missing required parameters: iss, client_id, login_hint, target_link_uri."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        platform = _find_platform(iss)
        if not platform:
            return Response(
                {"detail": "Unknown platform issuer. Configure LMS_LTI_PLATFORMS in settings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_client = (platform.get("client_id") or "").strip()
        if expected_client and client_id != expected_client:
            return Response({"detail": "client_id does not match registration."}, status=status.HTTP_403_FORBIDDEN)

        auth_endpoint = (platform.get("authorization_endpoint") or "").strip()
        if not auth_endpoint:
            return Response(
                {"detail": "Platform registration missing authorization_endpoint."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(24)
        request.session["lti_oidc"] = {
            "iss": iss,
            "client_id": client_id,
            "login_hint": login_hint,
            "target_link_uri": target_link_uri,
            "lti_message_hint": lti_message_hint,
            "deployment_id": deployment_id,
            "state": state,
            "nonce": nonce,
        }
        request.session.modified = True

        resume = request.build_absolute_uri("/api/v1/lti/login-resume/")
        if not request.user.is_authenticated:
            login_url = getattr(settings, "LOGIN_URL", "/accounts/login/")
            sep = "&" if "?" in login_url else "?"
            return HttpResponseRedirect(f"{login_url}{sep}next={quote(resume, safe='')}")

        return self._redirect_to_platform_authorize(request, platform, auth_endpoint, state, nonce, login_hint, client_id)

    def _redirect_to_platform_authorize(self, request, platform, auth_endpoint, state, nonce, login_hint, client_id):
        redirect_uri = (platform.get("tool_redirect_uri") or "").strip()
        if not redirect_uri:
            redirect_uri = request.build_absolute_uri("/api/v1/lti/launch/")
        q = {
            "scope": "openid",
            "response_type": "id_token",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "login_hint": login_hint,
            "state": state,
            "nonce": nonce,
            "response_mode": "form_post",
            "prompt": "none",
        }
        return HttpResponseRedirect(f"{auth_endpoint}?{urlencode(q)}")


class LtiOidcLoginResumeView(APIView):
    """After Django login, continue OIDC redirect to the platform."""

    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(getattr(settings, "LOGIN_URL", "/accounts/login/"))
        blob = request.session.get("lti_oidc") or {}
        iss = blob.get("iss")
        if not iss:
            return Response({"detail": "No LTI login session."}, status=status.HTTP_400_BAD_REQUEST)
        platform = _find_platform(iss)
        if not platform:
            return Response({"detail": "Platform registration missing."}, status=status.HTTP_400_BAD_REQUEST)
        auth_endpoint = (platform.get("authorization_endpoint") or "").strip()
        if not auth_endpoint:
            return Response({"detail": "authorization_endpoint missing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        client_id = blob.get("client_id") or platform.get("client_id")
        login_hint = blob.get("login_hint")
        state = blob.get("state")
        nonce = blob.get("nonce")
        redirect_uri = (platform.get("tool_redirect_uri") or "").strip()
        if not redirect_uri:
            redirect_uri = request.build_absolute_uri("/api/v1/lti/launch/")
        q = {
            "scope": "openid",
            "response_type": "id_token",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "login_hint": login_hint,
            "state": state,
            "nonce": nonce,
            "response_mode": "form_post",
            "prompt": "none",
        }
        return HttpResponseRedirect(f"{auth_endpoint}?{urlencode(q)}")


class LtiLaunchFormPostView(APIView):
    """
    Platform POSTs id_token here (response_mode=form_post).
    Validates RS256 signature via JWKS, state, and nonce (OIDC session).
    """

    permission_classes = [AllowAny]
    parser_classes = [FormParser, MultiPartParser]

    def post(self, request):
        token = request.POST.get("id_token")
        if not token and hasattr(request, "data"):
            token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token required."}, status=status.HTTP_400_BAD_REQUEST)

        st = request.POST.get("state")
        if not st and hasattr(request, "data"):
            st = request.data.get("state")
        if not st:
            return Response({"detail": "state required."}, status=status.HTTP_400_BAD_REQUEST)

        blob = request.session.get("lti_oidc") or {}
        if not blob:
            return Response(
                {"detail": "No LTI OIDC session. Open /api/v1/lti/login/ from the platform first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if st != blob.get("state"):
            return Response({"detail": "state mismatch."}, status=status.HTTP_400_BAD_REQUEST)

        platform = _find_platform(blob.get("iss") or "")
        if not platform:
            return Response({"detail": "Platform registration missing."}, status=status.HTTP_400_BAD_REQUEST)

        jwks_uri = (platform.get("jwks_uri") or "").strip()
        if not jwks_uri:
            return Response(
                {"detail": "jwks_uri missing in LMS_LTI_PLATFORMS for this issuer."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        issuer = (blob.get("iss") or "").strip()
        audience = (blob.get("client_id") or "").strip()
        nonce = blob.get("nonce") or ""

        verifier = LtiIdTokenVerifier(jwks_uri)
        try:
            claims = verifier.verify(
                token,
                issuer=issuer,
                audience=audience,
                nonce=nonce,
                leeway_seconds=_jwt_leeway(),
            )
        except LtiIdTokenValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        token_iss = (claims.get("iss") or "").strip()
        if token_iss != issuer:
            return Response({"detail": "id_token issuer does not match session."}, status=status.HTTP_400_BAD_REQUEST)

        lti_claims = LtiClaimsExtractor.extract(claims)
        target_from_session = blob.get("target_link_uri") or ""

        sub = (claims.get("sub") or "").strip()
        if request.user.is_authenticated and sub:
            from learning.models import LTIUserMapping

            LTIUserMapping.objects.update_or_create(
                issuer=issuer,
                subject=sub,
                defaults={"user": request.user},
            )

        course_slug = LtiCourseSlugResolver.resolve(claims)
        LtiResourceLinkPersistenceManager.persist_from_launch(claims, course_slug)

        del request.session["lti_oidc"]
        request.session.modified = True

        prefer_json = bool(getattr(settings, "LMS_LTI_LAUNCH_JSON_RESPONSE", False))
        if request.user.is_authenticated and course_slug and not prefer_json:
            return HttpResponseRedirect(f"/learn/{course_slug}")

        return Response(
            {
                "launch": "ok",
                "sub": claims.get("sub"),
                "lti": lti_claims,
                "target_link_uri": target_from_session,
                "course_slug": course_slug,
            },
            status=status.HTTP_200_OK,
        )
