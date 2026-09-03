# RazorRecover Dashboard (Phase 5)

Reads from the FastAPI backend's `/payment-failures`, `/payment-failures/{id}/audit-trail`,
and `/metrics` endpoints. Two-pane layout: a ledger of failures on the left,
the selected failure's full decision timeline on the right — modeled on the
"decision timeline" example in the project spec (payment failed → classified
→ policy checked → executed), since that's the single clearest way to show
the AI recommends and the policy layer decides, not the other way around.

Every failure and action carries its `LIVE_TEST_MODE` / `SIMULATED` provenance
tag, visibly, per the spec's honesty requirement — never presented as real
recovered money without that label.

## Setup

```bash
cd razorrecover-dashboard
npm install
cp .env.local.example .env.local
```

`.env.local` should point at your running backend (default `http://localhost:8000`).

## Run

Make sure the FastAPI backend (Phase 1-4) is running first, then:

```bash
npm run dev
```

Open `http://localhost:3000`. The dashboard polls the backend every 8 seconds,
so newly arrived webhooks show up without a manual refresh — useful for a
live demo where you trigger a failure and watch it appear.

## Known items before a public deploy

`npm audit` flags several Next.js 14.x advisories (mostly SSRF/cache-poisoning/DoS
classes affecting self-hosted production servers) and a PostCSS advisory.
None of these matter for local development or a demo against `localhost`,
but don't deploy this publicly without running `npm audit fix` (note: the
full fix is a Next.js 15/16 major-version upgrade, which is a bigger change
than worth risking this close to the deadline — fine to defer past the demo).

## Notes on the design
Deliberately not the generic rounded-card-with-shadow dashboard look — this
is styled like a financial ledger/audit statement (hairline rules, dense
rows, monospace for amounts/IDs, IBM Plex Serif for section headers), since
the subject matter is an audit trail for money decisions, not a marketing page.
