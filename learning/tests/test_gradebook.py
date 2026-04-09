from django.contrib.auth import get_user_model
from django.test import TestCase

from learning.methods.grade_aggregation import recalculate_enrollment_weighted_grade
from learning.models import (
    Course,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
    Grade,
    GradeCategory,
    GradeItem,
    LetterGradeScheme,
)

User = get_user_model()


class GradeAggregationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="grade-student",
            password="x",
            name="Grade Student",
            email="grade@student.test",
        )
        self.course = Course.objects.create(title="Grade Course", slug="grade-course", status="published")
        self.enr = Enrollment.objects.create(
            user=self.user,
            course=self.course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )

    def test_missing_grades_keeps_current_grade_empty(self):
        recalculate_enrollment_weighted_grade(self.enr)
        self.enr.refresh_from_db()
        self.assertIsNone(self.enr.current_grade_pct)
        self.assertEqual(self.enr.current_grade_letter, "")

    def test_zero_weight_categories_fallback_to_average(self):
        cat1 = GradeCategory.objects.create(course=self.course, name="C1", weight_pct=0, order=0)
        cat2 = GradeCategory.objects.create(course=self.course, name="C2", weight_pct=0, order=1)
        i1 = GradeItem.objects.create(category=cat1, source_type="manual", title="I1", max_points=100)
        i2 = GradeItem.objects.create(category=cat2, source_type="manual", title="I2", max_points=100)
        Grade.objects.create(enrollment=self.enr, grade_item=i1, points_earned=80)
        Grade.objects.create(enrollment=self.enr, grade_item=i2, points_earned=60)

        recalculate_enrollment_weighted_grade(self.enr)
        self.enr.refresh_from_db()
        self.assertEqual(str(self.enr.current_grade_pct), "70.00")

    def test_drop_lowest_is_applied_per_category(self):
        cat = GradeCategory.objects.create(course=self.course, name="Labs", weight_pct=100, drop_lowest_n=1, order=0)
        items = [
            GradeItem.objects.create(category=cat, source_type="manual", title="L1", max_points=100),
            GradeItem.objects.create(category=cat, source_type="manual", title="L2", max_points=100),
            GradeItem.objects.create(category=cat, source_type="manual", title="L3", max_points=100),
        ]
        Grade.objects.create(enrollment=self.enr, grade_item=items[0], points_earned=20)
        Grade.objects.create(enrollment=self.enr, grade_item=items[1], points_earned=80)
        Grade.objects.create(enrollment=self.enr, grade_item=items[2], points_earned=90)

        recalculate_enrollment_weighted_grade(self.enr)
        self.enr.refresh_from_db()
        # Lowest (20) dropped => avg(80,90)=85
        self.assertEqual(str(self.enr.current_grade_pct), "85.00")

    def test_letter_grade_scheme_resolution(self):
        cat = GradeCategory.objects.create(course=self.course, name="Final", weight_pct=100, order=0)
        item = GradeItem.objects.create(category=cat, source_type="manual", title="Exam", max_points=100)
        Grade.objects.create(enrollment=self.enr, grade_item=item, points_earned=92)
        LetterGradeScheme.objects.create(
            course=self.course,
            name="Default",
            bands=[
                {"letter": "A", "min_pct": 90, "max_pct": 100},
                {"letter": "B", "min_pct": 80, "max_pct": 89.99},
            ],
        )

        recalculate_enrollment_weighted_grade(self.enr)
        self.enr.refresh_from_db()
        self.assertEqual(self.enr.current_grade_letter, "A")
