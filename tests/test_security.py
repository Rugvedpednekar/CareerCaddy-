import unittest

from backend.security import create_access_token, decode_access_token, hash_password, verify_password


class SecurityTests(unittest.TestCase):
    def test_password_hash_never_contains_plaintext(self):
        password = "correct horse battery staple"
        encoded = hash_password(password)
        self.assertNotIn(password, encoded)
        self.assertTrue(verify_password(password, encoded))
        self.assertFalse(verify_password("wrong", encoded))

    def test_signed_token_round_trip_and_rejects_tampering(self):
        token = create_access_token("rugved_pednekar", "rugved", "a-long-test-secret")
        self.assertEqual(decode_access_token(token, "a-long-test-secret")["sub"], "rugved_pednekar")
        with self.assertRaises(ValueError):
            decode_access_token(token + "x", "a-long-test-secret")


if __name__ == "__main__":
    unittest.main()
