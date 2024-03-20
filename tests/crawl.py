import copy
import unittest
import unittest.mock

import utils.testargs
import onectf.jobs.crawl

base_test_data = utils.testargs.load_args('crawl.json')
base_crawl_data = onectf.jobs.crawl.CrawlerProgramData(
    type('testData', (), base_test_data)
)


class TestHosts(unittest.TestCase):
    def test_dummy(self):
        crawl_data = copy.deepcopy(base_crawl_data)
        with unittest.mock.patch('requests.get'):

            onectf.jobs.crawl.do_job(crawl_data, 'https://example.com')
            onectf.jobs.crawl.done(crawl_data)
            self.assertEqual(15, len(crawl_data.found_urls))
