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
4. Open it from the umbrelOS home screen. umbrelOS asks for your umbrelOS password first, then the app shows a few welcome screens that end with the creation of your account (a name and a password, typed twice). No code is needed on umbrelOS, because the umbrelOS login already protects that page.
5. Backups are in the `backups` folder of the app's data folder (in the Files app: `Apps/tombino104-personal-os/data`), and in Settings > Backups. The file `setup-code.txt` next to them holds the code needed to erase all data (Settings > Account, or the "start over" link on the login page); after erasing, the app starts again from the welcome screens.

## Where the data lives

Everything the app saves is in one folder, `Apps/tombino104-personal-os/data` (inside the container: `/data`). A backup is a copy of that folder. The code and the plugins are in the image, not in the data folder.

## Login

umbrelOS keeps its own login in front of the app (the default for umbrelOS apps), and Personal OS has its own login behind it. Write requests are accepted only from the same origin (the browser's `Sec-Fetch-Site` header), which keeps the app working behind any proxy. In the compose file, `SETUP_CODE_REQUIRED: "false"` lets the first account be created without the setup code, which is safe because the umbrelOS login protects that page.

## Updating

Bump the version in `umbrel-store/tombino104-personal-os/umbrel-app.yml` and the image tag in its `docker-compose.yml` after a new release image exists, and publish the store again. umbrelOS then offers the update. Migrations run at startup and never delete data.

## Before submitting to the official App Store

The community store above is the way to try the app on your own Umbrel. The official App Store takes apps through a pull request to [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps). The files for that pull request are in `umbrel-official/` (not published anywhere): see `umbrel-official/README.md` for the steps and the text of the pull request.

What is already settled:

- **App id:** `personal-os`, with no store prefix, in a folder of the same name.
- **Login and first run:** the umbrelOS login stays on; the first account is created in the browser without any code or file.
- **Images:** multi-arch (amd64 and arm64) and pinned with the digest of the index.
- **Icon and gallery:** left out; the pull request carries the screenshots and the logo.
- **License:** AGPL-3.0, an open source license.

What is still to do by hand: install, restart and update the app on a real umbrelOS device from the official packaging, run the repository's linter (`npm run lint:apps -- personal-os --check-images`), and confirm that port `8473` is free in the whole store.
