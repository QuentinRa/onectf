import copy
import unittest

import jobs.request

base_test_data = {
    "is_info": False,
    "is_debug": False,
    "threads": 1,

    "url": "https://example.com",
    "method": "GET",
    "headers": {},
    "body": None,
    "nr": False,

    "param": "x",
    "use_fuzzing": False,
    "use_json": False,
    "use_raw": False,

    "format": "html",

    "tamper": "aliases",
}

base_request_data = jobs.request.RequestProgramData(
    type('testData', (), base_test_data)
)


class TestRequest(unittest.TestCase):
    def test_get_request(self):
        request_data = copy.deepcopy(base_request_data)
        request_data.url = 'https://example.com'
        request_data.method = 'GET'
        request_data.param = 'param'
        (_, url, _, _, _) = request_data.inject_word('value')
        self.assertEqual(url, 'https://example.com?param=value')

    def test_post_request(self):
        request_data = copy.deepcopy(base_request_data)
        request_data.url = 'https://example'
        request_data.method = 'POST'
        request_data.param = 'param'
        (_, _, _, post_data, _) = request_data.inject_word('value')
        self.assertEqual({'param': 'value'}, post_data)

    def test_fuzzing_header(self):
        test_data = {}
        test_data.update(base_test_data)
        test_data.update({'headers': ['Cookie: X=Z; Y=FUZZ'], 'param': None, 'use_fuzzing': True })
        request_data = jobs.request.RequestProgramData(
            type('testData', (), test_data)
        )
        (_, _, headers, _, _) = request_data.inject_word('value')
        self.assertEqual(request_data.headers, {'Cookie': 'X=Z; Y=value'})

    def test_multiple_headers(self):
        test_data = {}
        test_data.update(base_test_data)
        test_data.update({'headers': ['Cookie: X=Z; Y=Z'] })
        request_data = jobs.request.RequestProgramData(
            type('testData', (), test_data)
        )
        self.assertEqual(request_data.headers, {'Cookie': 'X=Z; Y=Z'})


if __name__ == '__main__':
    unittest.main()
