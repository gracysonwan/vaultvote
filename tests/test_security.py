import os
import unittest

os.environ['SKIP_INIT_DB'] = '1'

from app import hash_password, make_salt, verify_password


class PasswordHelperTests(unittest.TestCase):
    def test_password_round_trip(self):
        password = 'correct horse battery staple'
        user_id = 'STUDENT001'
        salt = make_salt()
        stored = hash_password(password, salt, user_id)

        self.assertTrue(verify_password(password, salt, user_id, stored))
        self.assertFalse(verify_password('wrong password', salt, user_id, stored))


if __name__ == '__main__':
    unittest.main()
