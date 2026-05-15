# ERI

> AI-powered escrow and supplier verification for Nigerian B2B procurement, built on Squad APIs.

**Squad Hackathon 3.0 — Challenge 01: Proof of Life**

---

## What we're building 

A web app where a Nigerian pharmacy or hospital procurement officer can verify a drug supplier before paying them. The buyer enters supplier details, our AI runs three checks (identity verification via CAC + NAFDAC, transaction anomaly detection, and product image verification), and returns a trust score with explanations. If the buyer proceeds, payment goes into a Squad virtual account (escrow). On delivery, the buyer uploads photos of the goods received — our computer vision pipeline compares them against the original quote and verifies NAFDAC registration markings. If everything checks out, Squad's Transfer API releases funds to the supplier. If not, funds stay locked. **No score, no money moves.**

## The problem 

- The EFCC says **procurement and contract fraud account for 90%+ of Nigerian corruption** (Olukoyede, Jan 2025)
- NAFDAC issues a counterfeit drug alert almost weekly — fake malaria pills, fake oxytocin, fake antibiotics, all with forged NAFDAC numbers
- The estimate of fake/substandard drugs in Nigeria ranges from 13–15% (NAFDAC's own number) to ~50% (independent research)
- Nigerian businesses are losing money to **business email compromise (BEC) and supplier-bank-detail-change scams** — the Tribune (Jan 2026) flagged this as the top fraud vector for SMEs
- Pharmacies are doing manual verification today: emailing photos to foreign manufacturers to confirm authenticity. There is no system.

## The four pillars (and how we hit them)

| Pillar | How Eri satisfies it |
|---|---|
| **AI Automation** | Three engines: NLP/rules-based supplier identity verification, computer vision product comparison + OCR, and a trained anomaly detection model on transaction patterns |
| **Use of Data** | NAFDAC Greenbook lookup, CAC company verification, BVN-to-name matching, supplier transaction graph |
| **Squad APIs** | Virtual Accounts (escrow), Webhooks (payment confirmation), Transfer API (release), Payment Links (buyer onboarding) — all load-bearing |
| **Financial Innovation** | Reframes B2B payment from "trust-then-pay" to "verify-then-release" — turns Squad's payment rails into a fraud-prevention substrate |

## Demo scenario (the one we rehearse)

**Persona:** Procurement officer at a Lagos pharmacy chain ordering Coartem (artemether/lumefantrine) from a new supplier.

**Live demo flow (90 seconds on stage):**

1. Buyer enters supplier name, CAC number, bank account → **Eri verifies in <10s**: ✓ CAC active, ✓ Bank name matches business, ⚠️ NAFDAC license expired, ⚠️ 2 prior buyers reported delays. **Score: 62/100 (Amber)**.
2. Buyer chooses to proceed with full escrow. Squad creates a virtual account. Buyer transfers ₦1.2M.
3. Webhook fires → escrow funded.
4. Supplier "delivers." Buyer uploads photos of received drugs.
5. **Plot twist for the demo:** the photo shows a counterfeit Coartem with NAFDAC number `04-6433` (real fake number from NAFDAC Public Alert 023/2026).
6. Our CV pipeline OCRs the number, queries the Greenbook → **not registered to Novartis**. CV similarity: 71% match (visible packaging differences).
7. **Verdict: BLOCKED. Funds frozen. Dispute opened.**
8. Switch to legitimate supplier flow — same setup, real Coartem photo, NAFDAC verifies, CV similarity 96%, **Squad Transfer API releases funds live on stage**.

The live Squad transfer is the moment that wins the room.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                      │
│  ┌──────────────────────┐    ┌──────────────────────────┐    │
│  │  Buyer Flow (FE-1)   │    │ Supplier/Admin (FE-2)    │    │
│  │  - Verify supplier   │    │ - Supplier dashboard     │    │
│  │  - Create order      │    │ - Upload quote photos    │    │
│  │  - Fund escrow       │    │ - View payouts           │    │
│  │  - Upload delivery   │    │ - Admin: dispute review  │    │
│  └──────────────────────┘    └──────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
                              │
                              │  REST + WebSocket
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI / Python)                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  API LAYER                                                │ │
│  │  /auth   /suppliers   /orders   /verify   /webhooks       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Engine 1    │  │  Engine 2    │  │  Engine 3        │   │
│  │  Supplier    │  │  Product CV  │  │  Anomaly         │   │
│  │  Trust Score │  │  Verification│  │  Detection       │   │
│  │              │  │              │  │                  │   │
│  │ - CAC scrape │  │ - CLIP sim   │  │ - Isolation      │   │
│  │ - NAFDAC GB  │  │ - Tesseract  │  │   Forest (.pkl)  │   │
│  │ - Name match │  │   OCR        │  │ - Rule engine    │   │
│  │ - LLM invoice│  │ - NAFDAC GB  │  │   (BEC checks)   │   │
│  │   parse      │  │   crosscheck │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                              │                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  ESCROW ORCHESTRATOR                                      │ │
│  │  Squad Virtual Accounts ↔ Webhooks ↔ Transfer API         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                 │
│         ┌────────────────────┴────────────────────┐           │
│         ▼                                         ▼           │
│   ┌──────────┐                            ┌─────────────┐    │
│   │ Postgres │                            │ Redis (jobs)│    │
│   └──────────┘                            └─────────────┘    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  External integrations         │
              │  - Squad APIs (virtual acct,   │
              │    transfer, webhooks)         │
              │  - NAFDAC Greenbook (scrape)   │
              │  - CAC search (scrape)         │
              │  - OpenAI/Anthropic Vision     │
              └───────────────────────────────┘
```

## Tech stack (final)

**Backend:** Python 3.11, FastAPI, SQLAlchemy, Postgres (or SQLite for demo), Redis (optional, only if time permits async jobs)

**ML/AI:**
- `open_clip_torch` for image similarity (CLIP ViT-B-32, pretrained, runs on CPU)
- `pytesseract` for OCR
- `scikit-learn` for Isolation Forest (trained pre-hackathon, loaded as `.pkl`)
- `rapidfuzz` for name matching
- `Pillow` + `numpy` for EXIF/ELA tampering detection
- OpenAI Vision API (GPT-4o) OR Anthropic Claude Sonnet Vision for invoice parsing + adjudication
- `requests` + `beautifulsoup4` for CAC/NAFDAC scraping

**Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, lucide-react icons

**Payments:** Squad APIs (sandbox)

**Hosting (for demo):** Vercel (frontend) + Render or Railway (backend) — free tiers fine

## What "lightweight AI" means for the backend dev

The backend dev does **not** train models from scratch during the hackathon. Here's what they actually do:

| Task | What the dev does | Time |
|---|---|---|
| Engine 1 | Calls 4 Python functions I'll provide (CAC, NAFDAC, name match, LLM invoice parse). Aggregates scores. | 4-6 hrs |
| Engine 2 | Calls 3 Python functions: `clip_similarity()`, `extract_nafdac_number()`, `verify_nafdac()`. | 3-4 hrs |
| Engine 3 | Loads a pre-trained `.pkl` file with `joblib.load()`. Calls `model.predict_proba()`. | 1 hr |
| Pre-hackathon | Runs a Jupyter notebook (provided) that trains the Isolation Forest. Saves `.pkl`. | 1 hr |

Total AI-related work for backend dev: **~12 hours of API plumbing**, not ML engineering.

## Build plan: 4 days prep + hackathon weekend

See [`BUILD_PLAN.md`](./BUILD_PLAN.md) for the day-by-day breakdown.

## GitHub issues to create

See [`ISSUES.md`](./ISSUES.md) for the complete issue list, organized by team member and dependency order.

## Pitch and presentation

See [`PITCH.md`](./PITCH.md) for the demo script and slide outline.

## Risk register

See [`RISKS.md`](./RISKS.md) for what can go wrong and how we mitigate.

---

## Team

- **Backend dev** — FastAPI, AI engines (using prebuilt scripts), Squad integration, database
- **Frontend dev 1 (FE-1)** — Buyer flow (verification page, order/escrow, delivery upload)
- **Frontend dev 2 (FE-2)** — Supplier/admin flow + shared UI components + landing page

## Key external accounts to set up TODAY (Day 0)

1. **Squad sandbox account** → https://sandbox.squadco.com — get API keys
2. **Email Squad for business virtual account profiling** → `growth@squadco.com` cc `william.udousoro@habaripay.com`. Subject: *"Squad Hackathon 3.0 team — request for Virtual Account profiling"*. Mention you're hackathon participants. They expedite for hackathon teams.
3. **OpenAI API key** OR **Anthropic API key** (one or the other, ~$10 credit is plenty for the demo)
4. **GitHub repo** with all 3 team members added
5. **Vercel + Render accounts** for deployment

Everything else (NAFDAC Greenbook, CAC) is public — no signup needed.