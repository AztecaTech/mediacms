"""Keep CalendarEvent rows in sync with assignments, quizzes, cohorts, and modules."""

from __future__ import annotations

from datetime import datetime, time

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone as dj_tz

from learning.models import Assignment, CalendarEvent, CalendarEventType, Cohort, Module, Quiz


def _date_start(d):
    if d is None:
        return None
    naive = datetime.combine(d, time.min)
    if settings.USE_TZ:
        return dj_tz.make_aware(naive, dj_tz.get_current_timezone())
    return naive


def _date_end(d):
    if d is None:
        return None
    naive = datetime.combine(d, time(23, 59, 59))
    if settings.USE_TZ:
        return dj_tz.make_aware(naive, dj_tz.get_current_timezone())
    return naive


class AssignmentCalendarLinkManager:
    """Upsert or remove assignment due events."""

    SOURCE = "assignment"

    @classmethod
    def sync(cls, assignment: Assignment) -> None:
        course = assignment.lesson.module.course
        filt = {
            "course": course,
            "event_type": CalendarEventType.ASSIGNMENT_DUE,
            "source_type": cls.SOURCE,
            "source_id": assignment.pk,
        }
        if not assignment.due_at:
            CalendarEvent.objects.filter(**filt).delete()
            return
        CalendarEvent.objects.update_or_create(
            **filt,
            defaults={
                "title": f"Assignment due: {assignment.lesson.title}",
                "description": "",
                "starts_at": assignment.due_at,
                "ends_at": assignment.due_at,
                "url": f"/learn/{course.slug}",
            },
        )

    @classmethod
    def delete_for(cls, assignment_id: int) -> None:
        CalendarEvent.objects.filter(source_type=cls.SOURCE, source_id=assignment_id).delete()


class QuizCalendarLinkManager:
    """Upsert or remove quiz due events."""

    SOURCE = "quiz"

    @classmethod
    def sync(cls, quiz: Quiz) -> None:
        course = quiz.lesson.module.course
        filt = {
            "course": course,
            "event_type": CalendarEventType.QUIZ_DUE,
            "source_type": cls.SOURCE,
            "source_id": quiz.pk,
        }
        if not quiz.due_at:
            CalendarEvent.objects.filter(**filt).delete()
            return
        CalendarEvent.objects.update_or_create(
            **filt,
            defaults={
                "title": f"Quiz due: {quiz.lesson.title}",
                "description": "",
                "starts_at": quiz.due_at,
                "ends_at": quiz.due_at,
                "url": f"/learn/{course.slug}",
            },
        )

    @classmethod
    def delete_for(cls, quiz_id: int) -> None:
        CalendarEvent.objects.filter(source_type=cls.SOURCE, source_id=quiz_id).delete()


class CohortCalendarLinkManager:
    """Upsert cohort start/end milestones."""

    SOURCE = "cohort"

    @classmethod
    def sync(cls, cohort: Cohort) -> None:
        course = cohort.course
        start_f = {
            "course": course,
            "event_type": CalendarEventType.COHORT_START,
            "source_type": cls.SOURCE,
            "source_id": cohort.pk,
        }
        start_at = _date_start(cohort.start_date)
        CalendarEvent.objects.update_or_create(
            **start_f,
            defaults={
                "title": f"Cohort starts: {cohort.name}",
                "description": "",
                "starts_at": start_at,
                "ends_at": start_at,
                "url": f"/learn/{course.slug}",
            },
        )
        end_f = {
            "course": course,
            "event_type": CalendarEventType.COHORT_END,
            "source_type": cls.SOURCE,
            "source_id": cohort.pk,
        }
        if cohort.end_date:
            end_at = _date_end(cohort.end_date)
            CalendarEvent.objects.update_or_create(
                **end_f,
                defaults={
                    "title": f"Cohort ends: {cohort.name}",
                    "description": "",
                    "starts_at": end_at,
                    "ends_at": end_at,
                    "url": f"/learn/{course.slug}",
                },
            )
        else:
            CalendarEvent.objects.filter(**end_f).delete()

    @classmethod
    def delete_for(cls, cohort_id: int) -> None:
        CalendarEvent.objects.filter(source_type=cls.SOURCE, source_id=cohort_id).delete()


class ModuleCalendarLinkManager:
    """Module release reminder (relative offset; undated until cohort context)."""

    SOURCE = "module"

    @classmethod
    def sync(cls, module: Module) -> None:
        course = module.course
        filt = {
            "course": course,
            "event_type": CalendarEventType.MODULE_RELEASE,
            "source_type": cls.SOURCE,
            "source_id": module.pk,
        }
        if module.release_offset_days <= 0:
            CalendarEvent.objects.filter(**filt).delete()
            return
        CalendarEvent.objects.update_or_create(
            **filt,
            defaults={
                "title": f"Module opens: {module.title}",
                "description": (
                    f"Unlocks {module.release_offset_days} day(s) after each cohort start date "
                    f"(see your cohort for the exact date)."
                ),
                "starts_at": None,
                "ends_at": None,
                "url": f"/learn/{course.slug}",
            },
        )

    @classmethod
    def delete_for(cls, module_id: int) -> None:
        CalendarEvent.objects.filter(source_type=cls.SOURCE, source_id=module_id).delete()


@receiver(post_save, sender=Assignment)
def _assignment_cal_save(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    AssignmentCalendarLinkManager.sync(instance)


@receiver(post_delete, sender=Assignment)
def _assignment_cal_delete(sender, instance, **kwargs):
    AssignmentCalendarLinkManager.delete_for(instance.pk)


@receiver(post_save, sender=Quiz)
def _quiz_cal_save(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    QuizCalendarLinkManager.sync(instance)


@receiver(post_delete, sender=Quiz)
def _quiz_cal_delete(sender, instance, **kwargs):
    QuizCalendarLinkManager.delete_for(instance.pk)


@receiver(post_save, sender=Cohort)
def _cohort_cal_save(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    CohortCalendarLinkManager.sync(instance)


@receiver(post_delete, sender=Cohort)
def _cohort_cal_delete(sender, instance, **kwargs):
    CohortCalendarLinkManager.delete_for(instance.pk)


@receiver(post_save, sender=Module)
def _module_cal_save(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    ModuleCalendarLinkManager.sync(instance)


@receiver(post_delete, sender=Module)
def _module_cal_delete(sender, instance, **kwargs):
    ModuleCalendarLinkManager.delete_for(instance.pk)


def calendar_events_in_range(qs, from_dt=None, to_dt=None):
    """Filter queryset by starts_at window; undated events (e.g. relative module release) stay visible."""
    if from_dt is None and to_dt is None:
        return qs
    if from_dt and to_dt:
        window = Q(starts_at__isnull=True) | Q(starts_at__gte=from_dt, starts_at__lte=to_dt)
    elif from_dt:
        window = Q(starts_at__isnull=True) | Q(starts_at__gte=from_dt)
    else:
        window = Q(starts_at__isnull=True) | Q(starts_at__lte=to_dt)
    return qs.filter(window)
