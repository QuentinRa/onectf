# Host Editor

Given an IP address and a list of domains, add them to the host file (`/etc/hosts`). It ensures that previous records are updated or removed.

```bash
onectf hosts 127.0.0.1 a.test --dry
sudo onectf hosts 127.0.0.1 a.test b.test
```