"""Resolve course slug and persist LTI placements after a successful launch."""

from __future__ import annotations

from typing import Any

from django.conf import settings

from learning.models import Course, LTIResourceLink

LTI_CLAIM_CUSTOM = "https://purl.imsglobal.org/spec/lti/claim/custom"
LTI_CLAIM_CONTEXT = "https://purl.imsglobal.org/spec/lti/claim/context"
LTI_CLAIM_RESOURCE_LINK = "https://purl.imsglobal.org/spec/lti/claim/resource_link"


class LtiCourseSlugResolver:
    """Determine MediaCMS course slug from id_token claims (custom param, resource link, or default)."""

    @classmethod
    def resolve(cls, claims: dict[str, Any]) -> str | None:
        custom = claims.get(LTI_CLAIM_CUSTOM) or {}
        if isinstance(custom, dict):
            for key in ("course_slug", "courseSlug", "slug"):
                raw = (custom.get(key) or "").strip()
                if raw and Course.objects.filter(slug=raw).exists():
                    return raw
        rl = claims.get(LTI_CLAIM_RESOURCE_LINK) or {}
        ctx = claims.get(LTI_CLAIM_CONTEXT) or {}
        resource_link_id = (rl.get("id") or "").strip() if isinstance(rl, dict) else ""
        context_id = (ctx.get("id") or "").strip() if isinstance(ctx, dict) else ""
        if context_id and resource_link_id:
            link = LTIResourceLink.objects.filter(
                context_id=context_id,
                resource_link_id=resource_link_id,
            ).select_related("course").first()
            if link:
                return link.course.slug
        default_slug = (getattr(settings, "LMS_LTI_DEFAULT_COURSE_SLUG", None) or "").strip()
        if default_slug and Course.objects.filter(slug=default_slug).exists():
            return default_slug
        return None


class LtiResourceLinkPersistenceManager:
    """Upsert resource link when launch carries enough context + a known course."""

    @classmethod
    def persist_from_launch(cls, claims: dict[str, Any], course_slug: str | None) -> None:
        if not course_slug:
            return
        course = Course.objects.filter(slug=course_slug).first()
        if not course:
            return
        rl = claims.get(LTI_CLAIM_RESOURCE_LINK) or {}
        ctx = claims.get(LTI_CLAIM_CONTEXT) or {}
        if not isinstance(rl, dict) or not isinstance(ctx, dict):
            return
        resource_link_id = (rl.get("id") or "").strip()
        context_id = (ctx.get("id") or "").strip()
        if not resource_link_id or not context_id:
            return
        title = (rl.get("title") or "")[:255]
        LTIResourceLink.objects.update_or_create(
            context_id=context_id,
            resource_link_id=resource_link_id,
            defaults={
                "course": course,
                "title": title,
                "custom_json": {
                    "deployment_id": (claims.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id") or ""),
                },
            },
        )
