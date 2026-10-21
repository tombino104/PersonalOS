# Security

Personal OS is made for one person, running in a container on your own device behind a private network such as Tailscale. It is not meant to be exposed to the public internet.

## Supported versions

Only the latest release gets fixes.

## Reporting a vulnerability

Please do not open a public issue. Use [private vulnerability reporting](https://github.com/tombino104/PersonalOS/security/advisories/new) on GitHub, with the steps to reproduce and the version you tested. You will get an answer as soon as possible.

## Good to know

- Plugins run in the same process as the app. The permission rules protect your data from honest mistakes; they are not a security boundary against hostile code. Only install plugins you have read.
- The setup code in `data/setup-code.txt` can erase all data and create a new account. Anyone who can read your data folder can read it, as they can read the database itself.
