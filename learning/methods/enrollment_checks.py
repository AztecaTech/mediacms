from learning.models import CourseEnrollmentType, Enrollment, EnrollmentStatus


def user_in_rbac_group(user, rbac_group):
    if rbac_group is None:
        return False
    return rbac_group.memberships.filter(user=user).exists()


def missing_prerequisites(user, course):
    needed = course.prerequisites.filter(status="published")
    completed_ids = set(
        Enrollment.objects.filter(
            user=user,
            status=EnrollmentStatus.COMPLETED,
            course__in=needed,
        ).values_list("course_id", flat=True)
    )
    missing = []
    for prereq in needed:
        if prereq.id not in completed_ids:
            missing.append(prereq)
    return missing


def can_self_enroll(user, course):
    if course.status != "published":
        return False, "Course is not published."
    missing = missing_prerequisites(user, course)
    if missing:
        return False, "missing_prerequisites"

    et = course.enrollment_type
    if et == CourseEnrollmentType.OPEN:
        return True, None
    if et == CourseEnrollmentType.RBAC_GROUP:
        if course.rbac_group and user_in_rbac_group(user, course.rbac_group):
            return True, None
        return False, "Not a member of the required RBAC group."
    if et in (CourseEnrollmentType.INVITE, CourseEnrollmentType.APPROVAL):
        return False, "Self-enrollment is not available for this course."
    return False, "Unknown enrollment type."
