import unittest

import jobs.hosts

base_args = type('args', (), {'ip': '10.10.10.10', 'domain': ['a.test'], 'dry_run': True, 'no_merge': True,
                              'host_file': 'data/hosts/a', })


class TestHosts(unittest.TestCase):

    def _do_test(self, output, ip='10.10.10.10', domain=None, dry_run=True, no_merge=False, host_file='a'):
        if domain is None:
            domain = ['a.test']
        host_file = 'data/hosts/' + host_file
        args = type('args', (), {
            'ip': ip,
            'domain': domain,
            'dry_run': dry_run,
            'no_merge': no_merge,
            'host_file': host_file,
        })
        lines = jobs.hosts.do_job(args)
        self.assertEqual(output, lines)

    def test_empty_file(self):
        self._do_test('10.10.10.10     a.test')

    def test_already_in(self):
        self._do_test('10.10.10.10     a.test', host_file='b')

    def test_already_in_and_new(self):
        self._do_test('10.10.10.10     a.test b.test', domain=['a.test', 'b.test'], host_file='b')

    def test_already_in_new_ip(self):
        self._do_test('10.10.10.1     a.test', ip='10.10.10.1', domain=['a.test'], host_file='b')
        self._do_test(
            "10.10.10.10     a.test\n"
            + "10.10.10.1      b.test", ip='10.10.10.1', domain=['b.test'], host_file='c')


if __name__ == '__main__':
    unittest.main()
