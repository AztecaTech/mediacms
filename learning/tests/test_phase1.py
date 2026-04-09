from django.contrib.auth import get_user_model
from django.test import TestCase

from learning.methods import (
    apply_lesson_progress_heartbeat,
    can_self_enroll,
    mark_nonvideo_lesson_complete,
    missing_prerequisites,
)
from learning.models import (
    Course,
    CourseEnrollmentType,
    CourseStatus,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
    Lesson,
    LessonContentType,
    LessonProgressStatus,
    Module,
)
from rbac.models import RBACGroup, RBACMembership, RBACRole

User = get_user_model()


class EnrollmentPrerequisiteTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="stu", password="x", name="S", email="s@example.com")
        self.a = Course.objects.create(title="A", slug="course-a", status=CourseStatus.PUBLISHED)
        self.b = Course.objects.create(title="B", slug="course-b", status=CourseStatus.PUBLISHED)
        self.c = Course.objects.create(title="C", slug="course-c", status=CourseStatus.PUBLISHED)
        self.c.prerequisites.add(self.a)

    def test_missing_prerequisites(self):
        miss = missing_prerequisites(self.u, self.c)
        self.assertEqual(list(miss), [self.a])

    def test_can_enroll_after_complete(self):
        Enrollment.objects.create(
            user=self.u,
            course=self.a,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.COMPLETED,
        )
        miss = missing_prerequisites(self.u, self.c)
        self.assertEqual(list(miss), [])


class HeartbeatProgressTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="stu2", password="x", name="S2", email="s2@example.com")
        self.course = Course.objects.create(title="Vid", slug="vid-course", status=CourseStatus.PUBLISHED)
        self.mod = Module.objects.create(course=self.course, title="M", order=0)
        self.lesson = Lesson.objects.create(
            module=self.mod,
            title="L",
            order=0,
            content_type=LessonContentType.VIDEO,
        )
        self.enr = Enrollment.objects.create(
            user=self.u,
            course=self.course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )

    def test_heartbeat_marks_complete(self):
        lp = apply_lesson_progress_heartbeat(self.enr, self.lesson, 95, 100)
        self.assertEqual(lp.status, LessonProgressStatus.COMPLETED)
        self.enr.refresh_from_db()
        self.assertEqual(self.enr.completed_lessons_count, 1)

    def test_text_lesson_complete(self):
        les = Lesson.objects.create(
            module=self.mod,
            title="T",
            order=1,
            content_type=LessonContentType.TEXT,
            text_body="Body",
        )
        mark_nonvideo_lesson_complete(self.enr, les)
        self.enr.refresh_from_db()
        self.assertEqual(self.enr.completed_lessons_count, 2)


class RBACGroupEnrollTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="stu3", password="x", name="S3", email="s3@example.com")
        self.group = RBACGroup.objects.create(name="trainees")
        self.course = Course.objects.create(
            title="Gated",
            slug="gated",
            status=CourseStatus.PUBLISHED,
            enrollment_type=CourseEnrollmentType.RBAC_GROUP,
            rbac_group=self.group,
        )

    def test_can_self_enroll_in_group(self):
        RBACMembership.objects.create(user=self.u, rbac_group=self.group, role=RBACRole.MEMBER)
        ok, _msg = can_self_enroll(self.u, self.course)
        self.assertTrue(ok)

    def test_cannot_self_enroll_outside_group(self):
        ok, msg = can_self_enroll(self.u, self.course)
        self.assertFalse(ok)
        self.assertIn("RBAC", msg)
