# OneCTF - Modular CTF toolkit 

[![GitHub](https://img.shields.io/github/license/QuentinRa/onectf)](LICENSE)
[![GitHub issues closed](https://img.shields.io/github/issues-closed/QuentinRa/onectf?color=%23a0)](https://github.com/QuentinRa/onectf/issues)
[![GitHub pull requests closed](https://img.shields.io/github/issues-pr-closed/QuentinRa/onectf?color=%23a0)](https://github.com/QuentinRa/onectf/pulls)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/QuentinRa/onectf)](https://github.com/QuentinRa/onectf)

A set of CTF utilities. Mostly written for fun or to practice.

```bash
$ sudo apt install pipx
$ pipx ensurepath
$ pipx install git+https://github.com/QuentinRa/onectf.git
$ onectf -h
```

The documentation for each module:

* [AXFR](docs/axfr.md): find hidden subdomains vulnerable to zone transfer
* [Crawl](docs/crawl.md): HTML web crawler
* [Hosts](docs/hosts.md): host file management utility
* [Request](docs/request.md): request encoder
* [uffuf](docs/uffuf.md): file upload fuzzer