# oauth2imap

The utility provides the ability to access an IMAP4 account on a server with
XOAUTH2 authentication.

For now, the utility only supports outlook.office365.com. This may change if a
feature request is received.

There are several use-cases:

1. A server is created that proxies requests to the upstream imap4 server. The
   downstream server can be protected by another authentication method.

2. Operation in tunnel mode. Commands are received from stdin and sent to the
   upstream imap4 server and the response is broadcast to stdout. See for
   [more informartion](http://www.mutt.org/doc/manual/#tunnel).

## Configuration

The utility uses a config file to store authentication information.

```toml
[upstream]
authority = "https://login.microsoftonline.com/<<< tenant id or name >>>"
tenant-id = "<<< tenant id or naae >>>"
client-id = "<<< your client id >>>"
server = "outlook.office365.com"
port = 993
scope = [ "https://outlook.office365.com/.default" ]
username = "<<< your username or email here >>>"
tokens-file = "/home/user/.tokens"

[downstream]
server = "127.0.0.1"
port = 10143
username = "example"
password = "secret"
```

For tunnel mode, the `downstream` section is not required.

## Similar projects

* [email-oauth2-proxy](https://github.com/simonrob/email-oauth2-proxy) -- An
  IMAP/POP/SMTP proxy that transparently adds OAuth 2.0 authentication for email
  clients that don't support this method.

## License

oauth2imap is licensed under the GNU General Public License (GPL), version 3.
