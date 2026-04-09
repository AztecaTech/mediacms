from django.test import SimpleTestCase

from learning.methods.lti_jwt import LtiClaimsExtractor


class LtiClaimsExtractorTests(SimpleTestCase):
    def test_extract_strips_namespace(self):
        claims = {
            "sub": "user-1",
            "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "99",
            "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        }
        out = LtiClaimsExtractor.extract(claims)
        self.assertEqual(out["deployment_id"], "99")
        self.assertEqual(out["version"], "1.3.0")
        self.assertNotIn("sub", out)
