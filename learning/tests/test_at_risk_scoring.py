from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from learning.methods.at_risk_scoring import AtRiskScoringManager
from learning.models import (
    AnalyticsEvent,
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
)

User = get_user_model()


class AtRiskScoringManagerTests(TestCase):
    def test_tier_high_from_progress_and_grade(self):
        m = AtRiskScoringManager()
        r = m.tier_for(Decimal("10"), Decimal("45"))
        self.assertEqual(r.tier, "high")
        self.assertIn("progress_below_15_pct", r.reasons)
        self.assertIn("grade_below_50_pct", r.reasons)

    def test_tier_none_for_strong_learner(self):
        m = AtRiskScoringManager()
        r = m.tier_for(Decimal("90"), Decimal("95"))
        self.assertEqual(r.tier, "none")
        self.assertEqual(r.reasons, ())


class OrgAtRiskEnrollmentsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="mgr-risk",
            password="secret",
            name="Manager",
            email="mgr@test.com",
            is_manager=True,
        )
        self.student = User.objects.create_user(
            username="stu-risk",
            password="x",
            name="Student",
            email="stu@test.com",
        )
        self.course = Course.objects.create(
            title="Risk Course",
            slug="risk-course",
            status=CourseStatus.PUBLISHED,
        )
        Enrollment.objects.create(
            user=self.student,
            course=self.course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
            progress_pct=Decimal("10"),
            current_grade_pct=Decimal("55"),
        )

    def test_returns_rows_for_manager(self):
        self.client.login(username="mgr-risk", password="secret")
        response = self.client.get("/api/v1/admin/analytics/at-risk-enrollments/?min_tier=low&limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data["count"], 1)
        self.assertTrue(any(r["username"] == "stu-risk" for r in data["enrollments"]))

    def test_forbidden_for_non_manager(self):
        self.client.login(username="stu-risk", password="x")
        response = self.client.get("/api/v1/admin/analytics/at-risk-enrollments/")
        self.assertEqual(response.status_code, 403)

    def test_intervention_note_creates_event(self):
        enr = Enrollment.objects.get(user=self.student, course=self.course)
        self.client.login(username="mgr-risk", password="secret")
        response = self.client.post(
            "/api/v1/admin/analytics/intervention-notes/",
            data={"enrollment_id": enr.id, "note": "Emailed about pacing."},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            AnalyticsEvent.objects.filter(
                type="manager_intervention_note",
                metadata__enrollment_id=enr.id,
            ).exists()
        )
