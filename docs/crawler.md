# Crawler

Used to crawl a simple HTML/PHP website using:

* links (`<a>`),
* images (`<img>`), 
* scripts (`<script>`),
* javascript (`location.href`)

You can use the following flags:

```bash
onectf crawl -h
onectf crawl -u URL
onectf crawl [...] --pc # print HTML comments
onectf crawl [...] -k   # ignore SSL errors
onectf crawl [...] -L /path/to/list_of_endpoints.txt
onectf crawl [...] -o /tmp/output.txt
```

#### Testing

The script was tested on:

* [THM mustacchio](https://tryhackme.com/room/mustacchio) <small>(links, images, scripts)</small>
* [HTB Cap](https://app.hackthebox.com/machines/Cap) <small>(location.href, anchors, redirections)</small>

#### Roadmap

* [ ] Add support for verbose mode
* [ ] Add support for the sitemap.xml
* [ ] Add support for robots.txt
* [ ] Add custom filtering options + pretty header
* [ ] Add custom crawling options