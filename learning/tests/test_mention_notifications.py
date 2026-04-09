import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from learning.methods.mention_notifications import (
    MentionInAppNotificationDispatcher,
    extract_mention_usernames,
)
from learning.models import (
    Course,
    CourseStatus,
    Discussion,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
    Notification,
)

User = get_user_model()


class MentionParsingTests(TestCase):
    def test_extract_usernames_ordered_unique(self):
        self.assertEqual(extract_mention_usernames(""), [])
        self.assertEqual(
            extract_mention_usernames("Hi @bob and @alice @bob"),
            ["bob", "alice"],
        )
        self.assertEqual(extract_mention_usernames("@user.name-1_ok"), ["user.name-1_ok"])


class MentionDispatcherTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice-m",
            password="x",
            name="Alice",
            email="alice-m@test.com",
        )
        self.bob = User.objects.create_user(
            username="bob-m",
            password="x",
            name="Bob",
            email="bob-m@test.com",
        )
        self.course = Course.objects.create(
            title="Mention Course",
            slug="mention-course",
            status=CourseStatus.PUBLISHED,
        )
        self.course.instructors.add(self.alice)
        Enrollment.objects.create(
            user=self.bob,
            course=self.course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )

    def test_dispatch_skips_actor_and_creates_for_mentioned_member(self):
        n = MentionInAppNotificationDispatcher(
            course=self.course,
            actor_id=self.alice.id,
            body="@bob-m please review",
            title="Mention",
            url="/learn/mention-course",
            related_object_type="discussion_post",
            related_object_id=99,
        ).dispatch()
        self.assertEqual(n, 1)
        note = Notification.objects.get(recipient=self.bob, type="mention")
        self.assertIn("bob-m", note.body)

    def test_no_notification_when_mentioning_self(self):
        n = MentionInAppNotificationDispatcher(
            course=self.course,
            actor_id=self.bob.id,
            body="@bob-m only me",
            title="Mention",
            url="/x",
            related_object_type="discussion_post",
            related_object_id=1,
        ).dispatch()
        self.assertEqual(n, 0)
        self.assertFalse(Notification.objects.filter(recipient=self.bob, type="mention").exists())


class CourseMemberSearchApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create_user(
            username="inst-msearch",
            password="secret",
            name="Instructor Search",
            email="inst-msearch@test.com",
        )
        self.student = User.objects.create_user(
            username="stu-msearch",
            password="x",
            name="Student Search",
            email="stu-msearch@test.com",
        )
        self.outsider = User.objects.create_user(
            username="outsider-m",
            password="x",
            name="Out",
            email="out@test.com",
        )
        self.course = Course.objects.create(
            title="Search Course",
            slug="member-search-course",
            status=CourseStatus.PUBLISHED,
        )
        self.course.instructors.add(self.instructor)
        Enrollment.objects.create(
            user=self.student,
            course=self.course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )

    def test_forbidden_for_non_member(self):
        self.client.login(username="outsider-m", password="x")
        r = self.client.get("/api/v1/courses/member-search-course/members/search/?q=stu")
        self.assertEqual(r.status_code, 403)

    def test_student_finds_instructor_by_username_fragment(self):
        self.client.login(username="stu-msearch", password="x")
        r = self.client.get("/api/v1/courses/member-search-course/members/search/?q=inst")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        usernames = {row["username"] for row in data["results"]}
        self.assertIn("inst-msearch", usernames)

    def test_empty_query_returns_empty_results(self):
        self.client.login(username="stu-msearch", password="x")
        r = self.client.get("/api/v1/courses/member-search-course/members/search/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])


class DiscussionPostMentionIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create_user(
            username="inst-dm",
            password="secret",
            name="Inst",
            email="inst-dm@test.com",
        )
        self.student = User.objects.create_user(
            username="stu-dm",
            password="x",
            name="Stu",
            email="stu-dm@test.com",
        )
        self.course = Course.objects.create(
            title="DM Course",
            slug="discussion-mention-course",
            status=CourseStatus.PUBLISHED,
        )
        self.course.instructors.add(self.instructor)
        Enrollment.objects.create(
            user=self.student,
            course=self.course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )
        self.discussion = Discussion.objects.create(
            course=self.course,
            created_by=self.instructor,
            title="Thread",
        )

    def test_post_with_mention_creates_notification(self):
        self.client.login(username="stu-dm", password="x")
        r = self.client.post(
            f"/api/v1/discussions/{self.discussion.id}/posts/",
            data=json.dumps({"body": "Hi @inst-dm"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.instructor,
                type="mention",
                related_object_type="discussion_post",
            ).exists()
        )
