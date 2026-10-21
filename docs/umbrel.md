# Running on umbrelOS

Personal OS ships as a Docker image (`ghcr.io/tombino104/personalos`) and as a community app store for umbrelOS (the `umbrel-store/` folder).

## How it fits together

1. Every release tag (`v0.7.1`, ...) triggers the **Image** workflow on GitHub, which builds the image for `linux/amd64` and `linux/arm64` and publishes it to the GitHub container registry. The **CI** workflow runs all the tests on every push.
2. `umbrel-store/` is published as its own repository. umbrelOS reads it as a community app store.
3. umbrelOS pulls the image and starts the app behind its own app proxy, on port `47213`.

## Install

1. Create an empty repository for the store and publish `umbrel-store/` as its root (see `umbrel-store/README.md`).
2. In umbrelOS: App Store, menu at the top right, **Community App Stores**, add the repository address.
3. Install **Personal OS** from that store.
4. Open it (`http://umbrel.local:47213`). The first time, it asks for a one-time setup code. Find it in `setup-code.txt` inside the app's data folder (in the Files app: `Apps/tombino104-personal-os/data`).
5. Create your account. The code file disappears.

## Where the data lives

Everything the app saves is in one folder, `Apps/tombino104-personal-os/data` (inside the container: `/data`). A backup is a copy of that folder. The code and the plugins are in the image, not in the data folder.

## Login

Personal OS has its own login, so the umbrelOS app proxy does not ask for the umbrelOS password (`PROXY_AUTH_ADD: "false"`). Write requests are accepted only from the same origin (the browser's `Sec-Fetch-Site` header), which keeps the app working behind any proxy.

## Updating

Bump the version in `umbrel-store/tombino104-personal-os/umbrel-app.yml` and the image tag in its `docker-compose.yml` after a new release image exists, and publish the store again. umbrelOS then offers the update. Migrations run at startup and never delete data.
