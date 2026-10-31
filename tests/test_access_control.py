import unittest

from access_control import configured_admin_emails, is_admin_email


class AdminAllowlistTests(unittest.TestCase):
    def test_accepts_comma_and_semicolon_separated_secret(self):
        secrets = {"NESIL_ADMIN_EMAILS": "Admin@example.com; owner@example.com"}
        self.assertEqual(
            configured_admin_emails(secrets),
            {"admin@example.com", "owner@example.com"},
        )

    def test_accepts_list_secret(self):
        secrets = {"NESIL_ADMIN_EMAILS": ["Admin@example.com", "owner@example.com"]}
        self.assertTrue(is_admin_email(secrets, " ADMIN@example.com "))

    def test_non_admin_is_rejected(self):
        self.assertFalse(is_admin_email({"NESIL_ADMIN_EMAILS": "admin@example.com"}, "user@example.com"))

    def test_empty_email_is_never_admin(self):
        self.assertFalse(is_admin_email({"NESIL_ADMIN_EMAILS": ["admin@example.com"]}, ""))


if __name__ == "__main__":
    unittest.main()
