# Unrestricted File Upload Fuzzer

uffuf is a specialized tool inspired by the popular fuzzer [ffuf](https://github.com/ffuf/ffuf). It allows users to fuzz file names, content types, and other parameters, to assist in identifying vulnerabilities related to unrestricted file uploads in web applications. It's an alternative to Burp Suite or other web proxies.

#### Basic Usage

* Filename Fuzzing — Bypassing Filename Checks

```shell!
$ onectf uffuf -u https://example.com -p uploadFile -F myFile -w myWordlist -Fn dummyFUZZ
$ # Attempt by prepending a valid extension (filter)
$ onectf uffuf -u https://example.com -p uploadFile -F myFile -w myWordlist -Fn dummy.jpgFUZZ
$ # Attempt by appending a valid extension (misconfiguration, rare)
$ onectf uffuf -u https://example.com -p uploadFile -F myFile -w myWordlist -Fn dummyFUZZ.jpg
```

* MIME type — Investigate the filter

```shell!
$ # Attempt MIME type bypass
$ onectf uffuf [...] -Ft image/jpeg
$ # Attempt magic number bypass
$ onectf uffuf [...] -Ft image/jpeg --spoof
```

* MIME type Fuzzing — Detect Allowed MIME types

```shell!
$ # --spoof is optional if the server don't check the magic number
$ onectf uffuf -u https://example.com -p uploadFile -F myFile -w myWordlist -Ft FUZZ --spoof
```

#### Testing

* Blacklist some extensions (`https://academy.hackthebox.com/module/136/section/1288`)

```shell!
$ onectf uffuf -u <IP:port>/upload.php -p uploadFile -w web-extensions.txt -Fn testFUZZ -mr "File successfully uploaded"
```

* Blacklist and whitelist extensions (`https://academy.hackthebox.com/module/136/section/1289`)

```shell!
$ onectf uffuf -u <IP:port>/upload.php -p uploadFile -w web-extensions.txt -Fn testFUZZ.jpg -mr "File successfully uploaded"
```

* Blacklist and whitelist extensions, MIME type and magic number checking (`https://academy.hackthebox.com/module/136/section/1290`)

```shell!
$ file webshell.php.jpg
webshell.php.jpg: JPEG image data
$ onectf uffuf -u <IP:port>/upload.php -p uploadFile -w web-extensions.txt -F webshell.php.jpg -Fn test.jpgFUZZ -Ft image/jpg -mr "File successfully uploaded"
```

Alternatively, we can use the `--spoof` flag:

```shell!
$ onectf uffuf -u <IP:port>/upload.php -p uploadFile -w web-extensions.txt -F webshell.php -Fn test.jpgFUZZ -Ft image/jpg -mr "File successfully uploaded" --spoof
```

#### Missing Features

* Add an initial dummy test
* Improve Verbose Mode
* Add option to test if uploaded file is executable?