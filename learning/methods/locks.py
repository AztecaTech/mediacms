from datetime import timedelta

from django.utils import timezone


def module_unlock_date(module, cohort):
    if cohort is None:
        return None
    return cohort.start_date + timedelta(days=module.release_offset_days)


def is_module_locked_for_enrollment(module, enrollment):
    if enrollment.course.mode != "cohort" or enrollment.cohort is None:
        return False
    unlock = module_unlock_date(module, enrollment.cohort)
    if unlock is None:
        return False
    return timezone.now().date() < unlock


def is_lesson_locked_for_enrollment(lesson, enrollment):
    return is_module_locked_for_enrollment(lesson.module, enrollment)


def lesson_prerequisites_satisfied(lesson, enrollment):
    prereq_ids = set(lesson.prerequisites.values_list("pk", flat=True))
    if not prereq_ids:
        return True
    from learning.models import LessonProgress, LessonProgressStatus

    done = set(
        LessonProgress.objects.filter(
            enrollment=enrollment,
            lesson_id__in=prereq_ids,
            status=LessonProgressStatus.COMPLETED,
        ).values_list("lesson_id", flat=True)
    )
    return prereq_ids <= done
