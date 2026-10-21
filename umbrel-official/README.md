# Official umbrelOS App Store package

This folder is **not published anywhere**. It holds the files for a pull request to [getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps). Nothing here has been sent.

## What is different from the community store

- the app id is `personal-os` (no store prefix) and the folder has the same name;
- no `icon` and an empty `gallery`: the Umbrel team adds them, and the screenshots and logo go in the pull request body;
- `submission` is the pull request address: fill it in after opening the pull request;
- `releaseNotes` is empty for a new app.

The login of umbrelOS stays on, and `SETUP_CODE_REQUIRED: "false"` lets the first account be created in the browser without a code or a file.

## Steps

1. Fork `getumbrel/umbrel-apps` and copy the `personal-os` folder to the root of the fork.
2. Check that port `8473` is not used by another app in the store (change it in `umbrel-app.yml` if it is).
3. Run the linter from the fork: `npm run lint:apps -- personal-os --check-images`, and `git diff --check`.
4. Test on a real umbrelOS device: install the app from the fork, open it, create the account, restart, update, and check that the data is still there.
5. Open the pull request with one app only, with the text below, the logo and the screenshots from `docs/screenshots`.
6. Put the address of the pull request in `submission`.

For a new version: bump `version` and the image in `docker-compose.yml` (tag and digest of the multi-arch index, from `docker buildx imagetools inspect ghcr.io/tombino104/personalos:<version>`) in both this folder and `umbrel-store/`.

## Pull request text

**Personal OS 0.13.1**

A personal growth app for one person: six life areas, a relative score and an evening questionnaire. It is a mirror, not a judge (no streaks, ranks or notifications tied to points). Built-in calendar, plugins, nightly backups and restore, English and Italian.

- Upstream: https://github.com/tombino104/PersonalOS (AGPL-3.0)
- Image: `ghcr.io/tombino104/personalos:0.13.1`, public, `linux/amd64` and `linux/arm64`, pinned by the digest of the multi-arch index, built by GitHub Actions from the tag.
- Authentication: the umbrelOS login stays on. The app has its own account (one user) behind it; the first account is created in the browser with no default credentials and no code (`SETUP_CODE_REQUIRED=false`).
- Data: everything is in `${APP_DATA_DIR}/data` (SQLite database and backups).
- Permissions: no host access, no privileged mode, no extra ports.
- Testing: installed, opened, created the account, restarted and updated on umbrelOS (fill in the version and the device after testing).
