import copy
import scrapy.http
import unittest.mock
import onectf.jobs.crawl
import utils.testargs

base_test_data = utils.testargs.load_args('crawl.json')
base_crawl_data = onectf.jobs.crawl.CrawlerProgramData(
    type('testData', (), base_test_data)
)


class TestHosts(unittest.TestCase):
    def test_dummy(self):
        crawl_data = copy.deepcopy(base_crawl_data)
        spider = onectf.jobs.crawl.CustomCrawler(crawl_data)
        response = scrapy.http.HtmlResponse(
            url=crawl_data.url,
            body='<html><body>'
                 '<a href="a.php">test</a>'
                 '<a href="https://example.com/b.php">test</a>'
                 '<a href="/c.php">test</a>'
                 '<a href="mailto:john@doe.com">jane@doe.com</a>'
                 '<a href="#anchor">not new</a>'
                 '<a href="/">not new</a>'
                 '<a href="/myFolder/">myFolder</a>'
                 '<a href="resume.pdf">download</a>'
                 '<img src=secretFolder/myimage.png>'
                 '<script src=secretFolder/love.js />'
                 '<script src=secretFolder/secret.pdf />'
                 '<link rel="stylesheet" href="https://not.example.com/dummy.css">'
                 '<link rel="stylesheet" href="another.css">'
                 '<button onclick="location.href=\'dummy.php\'">clickme</button>'
                 '<button onclick=location.href="dummy.php">clickme</button>'
                 '<iframe src="resume2.pdf"></iframe>'
                 '<!-- \n'
                 'Secret API KEY: 1337        \n'
                 '-->'
                 '<!--Secret API KEY: 1337-1337-->'
                 '</html>',
            headers={
                'Content-Type': 'text/html'
            },
            encoding='utf-8'
        )
        # Some alternative to "yield"/crawler process
        _ = list(spider.parse(response))
        # Check results
        print(spider.results)
        self.assertEqual(msg="Emails", first=spider.results['emails'], second={
            'john@doe.com','jane@doe.com'
        })
        self.assertEqual(msg="Links", first=spider.results['links'], second={
            'https://example.com',
            'https://example.com/',
            'https://example.com/b.php',
            'https://example.com/c.php',
            'https://example.com/a.php',
            'https://example.com/secretFolder/',
            'https://example.com/dummy.php',
        })
        self.assertEqual(msg="Resources", first=spider.results['resources'], second={
            'css': {'https://example.com/another.css'},
            'js': {'https://example.com/secretFolder/love.js'},
            'pdf': {'https://example.com/resume.pdf', 'https://example.com/secretFolder/secret.pdf'},
            'images': {'https://example.com/secretFolder/myimage.png'}
        })
        self.assertEqual(msg="External", first=spider.results['external'], second={
            'https://not.example.com/dummy.css'
        })
        self.assertEqual(msg="Comments", first=spider.results['comments'], second={
            '<!--Secret API KEY: 1337-1337-->',
            '<!-- \nSecret API KEY: 1337        \n-->'
        })

