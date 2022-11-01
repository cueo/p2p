import unittest

from util import generate_id


class UtilTests(unittest.TestCase):
    def test_id(self):
        _id = generate_id()
        assert _id is not None


if __name__ == '__main__':
    unittest.main()
