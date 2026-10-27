# Health: daily steps from your phone

The health plugin shows one number per day, your steps, as a mirror next to your activities. It never enters your scores and never ticks an activity for you. A day without data stays empty.

Apple Health has no web API: the data lives on the iPhone, so something on the phone has to send it. The plugin gives that something an address and a token.

## Connect a phone

1. Turn the plugin on in **Settings > Plugins**, then open **More > Health**.
2. Under **Connect your phone**, give the device a name and press **Create token**. Copy the token at once: it is shown only once, and only its hash is stored.
3. Send the steps from the phone, in one of the ways below.

The token can only write steps. It cannot read anything, and it works for this plugin alone. Revoke it from the same page whenever you want. For the phone to reach the app, use the same https address you use for the app itself (see [running it](running.md), "Evening reminder", for Tailscale Serve).

## What the address accepts

`POST <your address>/api/v1/ingest/health` with the header `Authorization: Bearer <token>` (or `X-Api-Key: <token>`) and a JSON body, in any of these shapes:

```json
{ "steps": 8421 }
```

```json
{ "day": "2026-10-27", "steps": 8421 }
```

```json
{ "days": [{ "day": "2026-10-26", "steps": 9100 }, { "day": "2026-10-27", "steps": 8421 }] }
```

The first form means today. The export format of the Health Auto Export app also works as it is (see below): samples of the same day are added up, and metrics other than `step_count` are ignored.

A day keeps the highest count it received, because steps in a day can only grow. This makes sending the same day twice, or a partial export, harmless. Days in the future (more than one day ahead), negative numbers and absurd values are refused with a `422` and nothing from that request is stored.

## Option 1: an iPhone Shortcut

This needs no extra app. I have not tested the exact steps on a device, so treat them as a starting point.

1. In Shortcuts, create a shortcut with the action **Find Health Samples** (type Steps, start date is today), then **Calculate Statistics** (Sum).
2. Add **Get Contents of URL**: the address above, method `POST`, header `Authorization` = `Bearer <token>`, request body JSON with a number field `steps` set to the sum.
3. In **Automation**, run it every evening. The first run asks for permission to read Steps.

The phone must be able to reach the app when it runs, so Tailscale has to be connected on the phone. Whether iOS lets the automation run without asking each time is something to check.

## Option 2: Health Auto Export

[Health Auto Export](https://apps.apple.com/app/id1115567069) is an iPhone app that can post Apple Health data to a REST address on a schedule. Its automations need the paid tier or the free trial, and iOS limits background tasks, so it can be unreliable.

Create an automation of type **REST API**, with the address above, the header `Authorization: Bearer <token>`, the data type **Step Count**, export format **JSON** (version 2) and a daily summary.

## Privacy

Steps are stored in the database, so they are part of the backups and of the export. They are never sent anywhere else. The plugin cannot read your reports, scores or activities.
