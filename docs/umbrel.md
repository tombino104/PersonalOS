# Running on umbrelOS

Personal OS ships as a Docker image (`ghcr.io/tombino104/personalos`) and as a community app store for umbrelOS (the `umbrel-store/` folder).

## How it fits together

1. Every release tag (`v0.7.1`, ...) triggers the **Image** workflow on GitHub, which builds the image for `linux/amd64` and `linux/arm64` and publishes it to the GitHub container registry. The **CI** workflow runs all the tests on every push.
2. `umbrel-store/` is published as its own repository. umbrelOS reads it as a community app store.
3. umbrelOS pulls the image and starts the app behind its own app proxy, on port `8473`. (Ports 40000 to 49999 are reserved by umbrelOS for virtual machines, so the Umbrel port differs from the `47213` used for local Docker.)

## Install

1. Create an empty repository for the store and publish `umbrel-store/` as its root (see `umbrel-store/README.md`).
2. In umbrelOS: App Store, menu at the top right, **Community App Stores**, add the repository address.
3. Install **Personal OS** from that store.
4. Open it (`http://umbrel.local:8473`). The first time, it asks for a one-time setup code. Find it in `setup-code.txt` inside the app's data folder (in the Files app: `Apps/tombino104-personal-os/data`). The same file holds the code for the "start over" link on the login page, which erases all data.
5. Create your account. The code file disappears.

## Where the data lives

Everything the app saves is in one folder, `Apps/tombino104-personal-os/data` (inside the container: `/data`). A backup is a copy of that folder. The code and the plugins are in the image, not in the data folder.

## Login

Personal OS has its own login, so the umbrelOS app proxy does not ask for the umbrelOS password (`PROXY_AUTH_ADD: "false"`). Write requests are accepted only from the same origin (the browser's `Sec-Fetch-Site` header), which keeps the app working behind any proxy.

## Updating

Bump the version in `umbrel-store/tombino104-personal-os/umbrel-app.yml` and the image tag in its `docker-compose.yml` after a new release image exists, and publish the store again. umbrelOS then offers the update. Migrations run at startup and never delete data.

## Before submitting to the official App Store

The community store above is the way to try the app on your own Umbrel. The official App Store takes apps through a pull request to [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps); the same two files (`umbrel-app.yml` and `docker-compose.yml`) are reused, with these differences to settle first:

- **App id and folder:** the official store uses a plain lowercase id with no store prefix (for example `personal-os`).
- **Port:** it must be unique across the whole store; the linter checks it.
- **Gallery and icon:** leave `gallery: []` and no `icon`; the Umbrel team adds the images. Screenshots go in the pull request description.
- **Umbrel login:** the official packaging keeps the umbrelOS login in front of apps by default. Personal OS has its own login, so decide whether to keep both or to rely on the umbrelOS one.
- **First-run setup:** the app store standard asks that an app opens to a clear next step without reading files or logs. Today the first run asks for a code stored in `setup-code.txt`; this should be replaced (for example by relying on the umbrelOS login) before submitting.
- **License:** the documents read do not state a license rule. The license is currently PolyForm Noncommercial, which is not open source; ask the Umbrel team whether it is accepted before investing in the submission.
- **Checks:** install, restart and update the app on a real umbrelOS device, and run the repository's linter.
