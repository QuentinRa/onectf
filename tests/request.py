import copy
import unittest

import jobs.request


base_request_data = jobs.request.RequestProgramData(
    type('testData', (), {
        "is_verbose": False,

        "url": "https://example.com",
        "method": "GET",
        "headers": {},
        "body": None,
        "nr": False,
        "is_raw": False,

        "param": "x",

        "tamper": "aliases",
    })
)


class TestRequest(unittest.TestCase):
    def test_get_request(self):
        request_data = copy.deepcopy(base_request_data)
        request_data.url = 'https://example.com'
        request_data.method = 'GET'
        request_data.param = 'param'
        (url, _, _) = request_data.inject_word('value')
        self.assertEqual(url, 'https://example.com?param=value')

    def test_post_request(self):
        request_data = copy.deepcopy(base_request_data)
        request_data.url = 'https://example'
        request_data.method = 'POST'
        request_data.param = 'param'
        (_, post_data, _) = request_data.inject_word('value')
        self.assertEqual({'param': 'value'}, post_data)


if __name__ == '__main__':
    unittest.main()