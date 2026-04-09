import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from learning.models import LdapDirectorySource

User = get_user_model()


class LdapDirectoryApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="mgr-ldap",
            password="secret",
            name="Manager",
            email="mgr-ldap@test.com",
            is_manager=True,
        )
        self.user = User.objects.create_user(
            username="stu-ldap",
            password="x",
            name="Student",
            email="stu-ldap@test.com",
        )
        self.source = LdapDirectorySource.objects.create(
            name="test-ldap",
            server_uri="ldap://localhost:389",
            user_search_base="ou=people,dc=example,dc=com",
        )

    def test_list_for_manager(self):
        self.client.login(username="mgr-ldap", password="secret")
        response = self.client.get("/api/v1/admin/directory/ldap-sources/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "test-ldap")

    def test_list_forbidden_for_non_manager(self):
        self.client.login(username="stu-ldap", password="x")
        response = self.client.get("/api/v1/admin/directory/ldap-sources/")
        self.assertEqual(response.status_code, 403)

    def test_sync_updates_metadata(self):
        self.client.login(username="mgr-ldap", password="secret")
        response = self.client.post(
            f"/api/v1/admin/directory/ldap-sources/{self.source.pk}/sync/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.source.refresh_from_db()
        self.assertIsNotNone(self.source.last_sync_at)
        self.assertIn("No-op sync", self.source.last_sync_message)
