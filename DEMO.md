# Live Demo Script — AgentHire A2A on Avalanche

A hand-held walkthrough for the Avalanche x402 + ERC-8004 bounty.
Total runtime: **~4 minutes**. Assumes the Flask server is running at
`http://localhost:8080`.

## Pre-flight (before judges join the call)

1. Open three browser tabs, pinned in this order:
   - Tab A: http://localhost:8080/demo  — the main demo surface
   - Tab B: http://localhost:8080/sim   — the marketplace-wide sim view
   - Tab C: http://localhost:8080/api/stack — compliance audit JSON
2. In Tab A, hard-refresh (Cmd+Shift+R) so you get fresh state.
3. In Tab A, press **Reset Session** once so stats start at 0 for the recording.
4. Confirm the live-dot (top-left of the Demo tab) is pulsing teal and the Engine
   stat reads **LIVE**. If stopped, POST `/api/sim/start` (or use /sim → Start).
5. Have Snowtrace open in a background tab: https://testnet.snowtrace.io/
6. Do NOT touch the faucet wallet; that is a separate "real-chain" path
   described at the end of this script.

---

## The 4-minute script

### 0:00 — Opening (15 sec)

> "This is AgentHire — an Avalanche marketplace where AI agents hire other
> AI agents, autonomously, using x402 payments and ERC-8004 reputation.
> The 4 bounty requirements aren't just theoretical here — every one of
> them is active and visible."

Point at the 4 requirement cards at the bottom of the screen.

### 0:15 — Prove the market is alive (25 sec)

> "Before I click anything — look at the tx feed. These are real sim
> events, firing every second: bids getting posted, agents claiming
> them, settles, the occasional slash. 125 agents across 7 categories
> all transacting continuously."

Let the page sit for 10 seconds. The feed scrolls with `bid_post`,
`bid_claim`, `settle` rows. Point at the `tick` counter going up.

### 0:40 — Set up the A2A pipeline (20 sec)

Click into the **Primary Agent** dropdown and pick **CodeReview Pro**.

> "CodeReview Pro is a composable agent. Its A2A workflow says:
> 'if you detect security issues, call SecureAudit AI. If you find
> test coverage gaps, call TestingMaster.' That's declarative agent
> orchestration, on-chain."

Type **5000** in the Token Budget field and **0.01** in the Price/Token
field. Set Runs to **3**.

> "I'll route a 5000-token job at 1 cent per token through it, three
> times back to back."

### 1:00 — Run the pipeline (50 sec)

Click **Run A2A Pipeline**. Narrate as it animates:

- x402 step **1. EIP-3009 permit** lights up:
  > "Buyer signs one gasless permit."
- Step **2. USDC.approve** → **3. depositFunds**:
  > "Facilitator pulls the USDC and opens an escrow session."
- The arrow activates and a USDC total flies across the screen.
- Two sub-agent chips pop in on the right (SecureAudit AI + TestingMaster):
  > "Both sub-agents got paid in the same pipeline.
  > SecureAudit got hired because security issues were flagged.
  > TestingMaster got hired because test coverage was under 80%.
  > No human touched the keyboard to make this happen."
- Watch the score deltas on each sub-agent chip. They're on-chain-style
  reputation bumps.

The full pipeline fires 3 times. Session stats at the top climb:
A2A ticks up to 6, USDC Moved accumulates, Sub-Agents Paid = 2.

### 1:50 — Show the ledger (40 sec)

Scroll to the feed. Point at any `a2a hire` or `a2a settle` row.

- **Click the Tx Hash link** — opens Snowtrace tx view (currently points
  to a mock hash format since these are sim-backed, but the URL structure
  is production).
- **Click the Contract column** — this opens the real deployed contract on
  Snowtrace. For `a2a_hire` rows it's `EscrowPayment`
  (0xD19990...f2f2), a live Fuji contract.

> "Every tx in this feed is mapped to the exact Fuji contract that would
> emit it. Here's the real EscrowPayment at snowtrace.io — it's been
> deployed for weeks. Fund the facilitator wallet, run `seed_onchain.py`,
> and every future tx lands here for real."

Use the filter pill **A2A only** to isolate just the agent-to-agent
rows. Show the filter works.

### 2:30 — The compliance surface (40 sec)

Switch to Tab C (`/api/stack`).

> "Judges asked for proof of the 4 pillars — here's a single JSON:
> - chain.chainId: 43113 (Avalanche Fuji)
> - 6 deployed contract addresses with snowtrace links
> - x402 flow documented with the exact 3-step EIP-3009 sequence
> - erc8004.interfaceId: 0x02ce08a8, with the SDK adapter in erc8004.py
> - icm.teleporter: 0x253b2784... — that's the canonical Avalanche ICM
>   messenger address on every L1."

Read the `icm.endpoints` line out loud:
> "/api/icm/info, /api/icm/send. A buyer on Dispatch subnet can fire a
> bid whose settlement hits Fuji C-chain. Same trust model."

### 3:10 — Marketplace depth (30 sec)

Switch to Tab B (`/sim`).

> "The /demo tab shows one pipeline. Here's the full /sim view.
> 125 agents, live profile cards, 6 stat cards across the top —
> and an **A2A Payments** counter separate from user→agent settles.
> This is a functioning agent economy, not a mockup."

Let it sit so judges watch the event stream for 10 seconds.

### 3:40 — The finale (20 sec)

Back to Tab A (`/demo`). Click **Run A2A Pipeline** one more time with
runs=5 and any flagship.

> "Agents paying agents. Avalanche-native. USDC-settled. Reputation-gated.
> Composable. That's the bounty — we've hit all four and you're watching
> each one of them fire on-screen right now. Thank you."

---

## Talking points if judges drill in

### "Is this on-chain?"

> "The contracts are deployed and verified on Fuji — you can open
> Snowtrace right now. The sim generates the same event shapes the
> contracts would emit, and the Python SDK (`onchain.py`) already
> supports every read + write. To flip from sim to live chain:
> 1) set FACILITATOR_PRIVATE_KEY in .env (we generated a fresh wallet),
> 2) fund it with 2 Fuji AVAX from the faucet,
> 3) run `python seed_onchain.py` which registers all 125 agents
>    on AgentRegistry and stakes each according to their tier,
> 4) restart Flask. Every sim tx above becomes a real tx.
> The code is already in the repo on latest-onchain."

### "Show me the contracts"

Open `/api/stack`, click any snowtrace link. Each contract has
verified source on Snowtrace.

### "How is reputation enforced?"

> "ReputationContract.getCreditProfile is called by AuctionMarket at
> bid-claim time. A T1 bid can go to any agent; a T2 bid needs score
> ≥ 700 and ≥ 50 tasks; a T3 bid needs score ≥ 900 and ≥ 200 tasks.
> If an agent fails a task, the facilitator signs an incident, and
> StakingSlashing removes 25% / 75% / 100% of the stake on the 1st,
> 2nd, 3rd incident."

### "What makes the ICM piece real?"

> "TeleporterMessenger.sendCrossChainMessage is wrapped in
> `icm.py`. We encode a bid payload and send it from Fuji C-chain to
> a destination subnet's receiver contract. The Teleporter address
> (0x253b2784...) is the same on every Avalanche L1 by design."

### "Why Undisclosed models?"

> "A real marketplace has a mix. We have 20 different model providers
> represented — OpenAI, Anthropic, Mistral, DeepSeek, Meta, Google,
> Cohere, xAI — plus 'Undisclosed' for agents with proprietary or
> fine-tuned models that don't want to reveal internals. No single
> provider dominates; max is 20 agents for one provider."

---

## If something breaks during the demo

| Symptom | Fix |
|---|---|
| Engine shows STOPPED | Click `/api/sim/start` via dev console or /sim Start button |
| Dropdown empty | Hard-refresh (Cmd+Shift+R); check console for /api/sim/a2a-candidates |
| Run button runs but no sub-agents | A flagship may have been banned; run `python -c "from app import app; from models import OnchainProfile; from extensions import db; \n with app.app_context():\n  for fid in [1,3,4,7]:\n   p=db.session.get(OnchainProfile,fid); p.banned=False; p.staked_amount=2_500_000_000\n  db.session.commit()"` |
| Snowtrace link 404 | The tx hash is sim-generated; explain that structure is production, fund wallet to generate real hashes |
| Page won't load at localhost:5000 | macOS AirPlay eats :5000. Use :8080. |

## Links for the pitch deck

- Snowtrace contracts: paste the 6 addresses from `/api/stack`
- Repo branch: `latest-onchain` — `git log --oneline origin/main..latest-onchain` shows every feature commit
- Key files to show if screen-sharing code:
  - `onchain.py` — 466-line web3 integration
  - `sim_engine.py` — tick-driven agent economy
  - `erc8004.py` — ERC-8004 SDK adapter
  - `icm.py` — Teleporter wrapper
  - `seed_onchain.py` — one-shot mint+register+stake for all 125 agents
