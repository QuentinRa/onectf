# OneCTF

A set of utilities. Mostly written for fun or to practice.

## Crawler

Used to crawl a simple HTML/PHP website using links (`<a>`), images (`<img>`), scripts (`<script>`), javascript (`location.href`), and that's all for now.

```bash
onectf crawl -h
onectf crawl -u URL -o /tmp/output.txt
onectf crawl -u URL -o /tmp/output.txt -k # ignore SSL errors
```

Tested on:

* [THM mustacchio](https://tryhackme.com/room/mustacchio) <small>(links, images, scripts)</small>
* [HTB Cap](https://app.hackthebox.com/machines/Cap) <small>(location.href, anchors, redirections)</small>

Roadmap

* [ ] Add support for verbose mode
* [ ] Add support for the sitemap.xml
* [ ] Add support for robots.txt
* [ ] Test it on sqlmap HTB final assessment
* [ ] Add custom filtering options + pretty header
* [ ] Add custom crawling options
* [ ] Use Burp/ZAP exclude list

## Host Editor

Given an IP address and a list of domains, add them to the host file (`/etc/hosts`). It ensures that previous records are updated or removed.

```bash
onectf hosts 127.0.0.1 hello --dry
sudo onectf hosts 127.0.0.1 hello hello.test
```