import unittest

import jobs.utils.tampering


class TestRequest(unittest.TestCase):
    def test_base64(self):
        tamper = jobs.utils.tampering.TamperingHandler("base64,md5")
        encoded = tamper.apply("1")
        self.assertEqual(encoded, "cdd96d3cc73d1dbdaffa03cc6cd7339b")


if __name__ == '__main__':
    unittest.main()