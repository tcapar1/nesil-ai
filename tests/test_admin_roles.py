import unittest
from access_control import configured_admin_emails, is_admin_email


class AdminRoleTests(unittest.TestCase):
    def test_admin_email_list_is_case_insensitive(self):
        secrets = {"NESIL_ADMIN_EMAILS": ["Owner@Example.com", " second@example.com "]}
        self.assertTrue(is_admin_email(secrets, "owner@example.com"))
        self.assertTrue(is_admin_email(secrets, "SECOND@example.com"))
        self.assertFalse(is_admin_email(secrets, "user@example.com"))

    def test_comma_separated_value(self):
        self.assertEqual(configured_admin_emails({"NESIL_ADMIN_EMAILS": "a@example.com, b@example.com"}),
                         {"a@example.com", "b@example.com"})

    def test_missing_admin_list_fails_closed(self):
        self.assertFalse(is_admin_email({}, "owner@example.com"))


if __name__ == "__main__":
    unittest.main()
