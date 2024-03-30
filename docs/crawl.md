# Crawler

Used to crawl a simple HTML/PHP website using:

* links (`<a>`),
* images (`<img>`), 
* scripts (`<script>`),
* javascript (`location.href`)
* robots file (`/robots.txt`)

You can use the following flags:

```bash
onectf crawl -h
onectf crawl -u URL
onectf crawl [...] --comments # print HTML comments
onectf crawl [...] --emails   # print emails
onectf crawl [...] -k         # ignore SSL errors
onectf crawl [...] -L /path/to/list_of_endpoints.txt
onectf crawl [...] -o /tmp/output.txt
onectf crawl [...] --external # also list external URLs
```

## Testing

The script was tested on:

* [THM mustacchio](https://tryhackme.com/room/mustacchio) <small>(links, images, scripts)</small>
* [HTB Cap](https://app.hackthebox.com/machines/Cap) <small>(location.href, anchors, redirections)</small>
* [THM GamingServer](https://tryhackme.com/room/gamingserver)  <small>(weird robots.txt)</small>
* [THM Archangel](https://tryhackme.com/r/room/archangel)  <small>(emails)</small>

## Roadmap

* [ ] Add support for the sitemap.xml
* [ ] Add custom filtering options + pretty header
* [ ] Add custom crawling options