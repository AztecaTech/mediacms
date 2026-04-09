from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from learning.models import (
    Course,
    CourseMode,
    CourseStatus,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
)
from learning.methods.roster_csv_import import RosterCsvImportManager, RosterCsvImportError

User = get_user_model()


class RosterCsvImportManagerTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="inst-roster",
            password="x",
            name="Instructor",
            email="inst@roster.test",
        )
        self.student = User.objects.create_user(
            username="stu-roster",
            password="x",
            name="Student",
            email="stu@roster.test",
        )
        self.course = Course.objects.create(
            title="Roster Course",
            slug="roster-course",
            status=CourseStatus.PUBLISHED,
            mode=CourseMode.ASYNC,
        )
        self.course.instructors.add(self.instructor)

    def test_creates_enrollment_by_username(self):
        csv_text = "username,role,status\nstu-roster,student,active\n"
        summary = RosterCsvImportManager(self.course, self.instructor).run(csv_text)
        self.assertEqual(summary.created, 1)
        self.assertEqual(summary.failed, 0)
        enr = Enrollment.objects.get(user=self.student, course=self.course)
        self.assertEqual(enr.role, EnrollmentRole.STUDENT)
        self.assertEqual(enr.status, EnrollmentStatus.ACTIVE)

    def test_requires_username_or_email_header(self):
        with self.assertRaises(RosterCsvImportError):
            RosterCsvImportManager(self.course, self.instructor).run("a,b\n1,2\n")

    def test_unknown_user_row_fails(self):
        csv_text = "username\nnobody\n"
        summary = RosterCsvImportManager(self.course, self.instructor).run(csv_text)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(summary.created, 0)


class CourseRosterCsvImportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create_user(
            username="inst-api",
            password="secret",
            name="Instructor",
            email="inst-api@test.com",
        )
        self.student = User.objects.create_user(
            username="stu-api",
            password="x",
            name="Student",
            email="stu-api@test.com",
        )
        self.course = Course.objects.create(
            title="API Roster",
            slug="api-roster-course",
            status=CourseStatus.PUBLISHED,
        )
        self.course.instructors.add(self.instructor)

    def test_post_import_creates_enrollment(self):
        self.client.login(username="inst-api", password="secret")
        csv_text = "username,email\nstu-api,stu-api@test.com\n"
        response = self.client.post(
            "/api/v1/courses/api-roster-course/roster/import/",
            data={"file": SimpleUploadedFile("r.csv", csv_text.encode("utf-8"), content_type="text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created"], 1)
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course).exists())

    def test_forbidden_for_non_instructor(self):
        self.client.login(username="stu-api", password="x")
        csv_text = "username\nstu-api\n"
        response = self.client.post(
            "/api/v1/courses/api-roster-course/roster/import/",
            data={"file": SimpleUploadedFile("r.csv", csv_text.encode("utf-8"))},
        )
        self.assertEqual(response.status_code, 403)
