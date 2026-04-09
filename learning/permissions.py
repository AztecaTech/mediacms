from rest_framework import permissions


def _is_global_instructor(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return bool(getattr(user, "is_editor", False))


def is_course_instructor(user, course):
    if not user or not user.is_authenticated:
        return False
    if _is_global_instructor(user):
        return True
    return course.instructors.filter(pk=user.pk).exists()


def is_course_staff(user, course):
    if is_course_instructor(user, course):
        return True
    from learning.models import Enrollment, EnrollmentRole, EnrollmentStatus

    return Enrollment.objects.filter(
        course=course,
        user=user,
        status=EnrollmentStatus.ACTIVE,
        role__in=(EnrollmentRole.INSTRUCTOR, EnrollmentRole.TA),
    ).exists()


def is_enrolled_student(user, course):
    from learning.models import Enrollment, EnrollmentRole, EnrollmentStatus

    return Enrollment.objects.filter(
        course=course,
        user=user,
        status=EnrollmentStatus.ACTIVE,
        role=EnrollmentRole.STUDENT,
    ).exists()


def get_active_enrollment(user, course, cohort=None):
    from learning.models import Enrollment, EnrollmentStatus

    qs = Enrollment.objects.filter(course=course, user=user, status=EnrollmentStatus.ACTIVE)
    if cohort is None:
        return qs.filter(cohort__isnull=True).first()
    return qs.filter(cohort=cohort).first()


def is_active_course_member(user, course):
    """Any active enrollment role, or global/course instructor."""
    if not user or not user.is_authenticated:
        return False
    if is_course_instructor(user, course):
        return True
    from learning.models import Enrollment, EnrollmentStatus

    return Enrollment.objects.filter(
        user=user,
        course=course,
        status=EnrollmentStatus.ACTIVE,
    ).exists()


class IsCourseEditorOrReadOnly(permissions.BasePermission):
    """Create course: global editor. Update course: instructor or global editor."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == "POST":
            return _is_global_instructor(request.user)
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        from learning.models import Course

        if isinstance(obj, Course) and obj.status != "published":
            if not request.user.is_authenticated:
                return False
            if _is_global_instructor(request.user):
                return True
            return is_course_instructor(request.user, obj)
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_course_instructor(request.user, obj)


class IsCourseInstructorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        course = getattr(obj, "course", None) or obj
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_course_instructor(request.user, course)


class IsEnrolledOrInstructor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        course = obj.module.course if hasattr(obj, "module") else obj.course
        if is_course_instructor(request.user, course):
            return True
        from learning.models import Enrollment, EnrollmentStatus

        return Enrollment.objects.filter(
            user=request.user,
            course=course,
            status=EnrollmentStatus.ACTIVE,
        ).exists()


class IsOwnerOrInstructorForProgress(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        course = obj.lesson.module.course
        if obj.enrollment.user_id == request.user.id:
            return True
        return is_course_instructor(request.user, course)
