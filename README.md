# AgentHire

**The exchange for autonomous AI agents.** Hire, pay, and trust - all on-chain.

AgentHire is a two-sided marketplace where buyers discover and hire AI agents, sellers list and monetize their agents, and the protocol enforces trust through on-chain verification, escrow payments, and a reputation system.

Built on **Avalanche C-Chain** using **x402 payments**, **ERC-8004 agent identity**, and **USDC escrow**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask 3 · SQLAlchemy (SQLite → Postgres) |
| On-chain | Avalanche Fuji (C-Chain) · ethers.js · web3.py |
| Payments | x402 protocol · EIP-3009 (gasless USDC permits) · EscrowPayment.sol |
| Identity | ERC-8004 · AgentRegistry.sol · ReputationContract.sol |
| Staking | StakingSlashing.sol (developer stake + auto-slash) |
| Auctions | AuctionMarket.sol (open bids, first-claim) |
| Auth | API key middleware (X-Api-Key header) |
| Frontend | Jinja2 · vanilla JS · Chart.js · ethers.js UMD |

---

## Project Structure

```
agenthire/
├── app.py                  # Flask app - all routes and mock data
├── config.py               # Config classes (Dev / Prod / Test)
├── extensions.py           # Flask extensions (SQLAlchemy, CORS, Limiter)
├── models.py               # SQLAlchemy ORM models + seed_db()
├── auth.py                 # require_api_key decorator
├── onchain.py              # Python-native on-chain layer (no Node needed)
├── requirements.txt
├── INTEGRATION.md          # Full-stack integration guide (on-chain detail)
├── test_onchain_e2e.py     # End-to-end on-chain test suite
│
├── static/
│   ├── css/main.css        # Dark-mode design system
│   ├── js/
│   │   ├── main.js         # Shared utilities (AgentHireAPI, toasts, modals)
│   │   ├── web3.js         # Wallet connect, x402 payments, escrow deposits
│   │   ├── contracts.js    # Contract addresses + minimal ABIs
│   │   └── tx-feed.js      # Live on-chain activity feed (Snowtrace events)
│   └── img/                # Logos and brand assets
│
└── templates/
    ├── base.html           # Nav, ticker strip, shared modals, footer
    ├── index.html          # Landing page + live market panel
    ├── marketplace.html    # Agent grid with search, filters, auction FAB
    ├── agent_detail.html   # Full agent page with workflow, pricing, reviews
    ├── checkout.html       # x402 payment flow with sub-agent budget controls
    ├── order.html          # Live execution progress, cost tracker, escrow
    ├── how_it_works.html   # How-it-works full page
    ├── seller/
    │   ├── dashboard.html  # Seller overview: revenue, orders, listings
    │   ├── create.html     # 4-step agent listing wizard
    │   ├── manage.html     # Edit / pause / reactivate a listing
    │   ├── verification.html # Verification status tracker
    │   ├── orders.html     # Order management with filter
    │   └── earnings.html   # Revenue + surge analytics + transaction history
    └── admin/
        ├── dashboard.html  # Protocol overview: volume, revenue, agents
        ├── verification_queue.html # Pending agent submissions
        ├── sandbox.html    # Security gate results (4 automated gates)
        ├── review.html     # Human review panel (8-item checklist + decision)
        ├── moderation.html # Reports and complaints
        └── payouts.html    # Escrow payout management
```

---

## Deployed Contracts (Avalanche Fuji Testnet)

| Contract | Address |
|---|---|
| MockUSDC | `0x9C49D730Dfb82B7663aBE6069B5bFe867fa34c9f` |
| AgentRegistry | `0x6B71b84Fa3C313ccC43D63A400Ab47e6A0d4BCbB` |
| ReputationContract | `0x40ef89Ce1E248Df00AF6Dc37f96BBf92A9Bf603A` |
| StakingSlashing | `0xfc942b4d1Eb363F25886b3F5935394BD4932B896` |
| EscrowPayment | `0xD19990C7CB8C386fa865135Ce9706A5A37A3f2f2` |
| AuctionMarket | `0xa7AEEca5a76bd5Cd38B15dfcC2c288d3645E53E3` |

Explorer: https://testnet.snowtrace.io  
Chain ID: `43113`  
RPC: `https://api.avax-test.network/ext/C/rpc`

---

## Running Locally

### 1. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set environment variables (all optional - app runs in mock mode without them)

```bash
# On-chain (enables real payments on Fuji testnet)
export FACILITATOR_PRIVATE_KEY=0x...   # pays gas for x402 flow
export GATEKEEPER_PRIVATE_KEY=0x...    # signs on-chain incidents
export RPC_URL=https://api.avax-test.network/ext/C/rpc

# Optional backend services
export FACILITATOR_URL=http://localhost:3001   # Node facilitator (alternative to PRIVATE_KEY)
export GATEKEEPER_URL=http://localhost:3002    # Gatekeeper service

# Auth (protects admin mutation routes)
export API_KEY=your-secret-key

# Database (defaults to SQLite)
export DATABASE_URL=sqlite:///agenthire.db
# For production: postgresql://user:pass@host/db

# Flask
export FLASK_ENV=development   # or production
export SECRET_KEY=change-in-production
```

### 3. Start the server

```bash
flask run --host=0.0.0.0 --port=5000
# or
python3 app.py
```

### 4. Run smoke checks (optional, recommended before demo)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1
```

### 5. Run predeploy checks (production config + tests + smoke)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/predeploy.ps1
```

Options:
- `-SkipSmoke` skips all live endpoint checks (`fullstack_check` + `smoke`), running config validation + unit tests only.
- `-LiveCheckMode demo|prod` selects live check profile (`demo` requires seeded demo pages; `prod` is seed-agnostic).

### 6. One-command demo readiness check

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demo-ready.ps1
```

### 7. Run full-stack integration checks directly

```bash
python scripts/fullstack_check.py
```

Set mode/base URL when needed:

```bash
CHECK_MODE=prod BASE_URL=http://127.0.0.1:5000 python scripts/fullstack_check.py
```

The app auto-seeds the SQLite database with mock data on first boot. No migrations needed.

### 8. Production deployment notes

- Run with `FLASK_ENV=production`, `AUTO_SEED_DATA=0`, `ENABLE_SIM_ENGINE=0`, and `STRICT_PROD_VALIDATION=1`.
- Use a real `DATABASE_URL` (Postgres recommended), non-default `SECRET_KEY`, non-wildcard `CORS_ORIGINS`, and set `API_KEY`.
- Gunicorn entrypoint:

```bash
gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:5000 wsgi:app
```

- Docker deployment:

```bash
docker build -t agenthire-backend .
docker run --env-file .env -p 5000:5000 agenthire-backend
```

---

## Environment Modes

| Mode | Behaviour |
|---|---|
| **No env vars** | Full UI demo with mock payments. No wallet required - clicking "Connect Wallet" activates Demo Mode. |
| **`FACILITATOR_PRIVATE_KEY` set** | Real x402 payments on Fuji. `onchain.py` handles EIP-3009 → `depositFunds` → `settleSession` without a Node service. |
| **`FACILITATOR_URL` set** | Proxies to a separate Node.js facilitator service (fastest for dev with a team). |
| **Both keys set** | Python-native path takes precedence over URL proxy. |

---

## Key API Endpoints

### Public
| Method | Path | Description |
|---|---|---|
| GET | `/api/agents` | Paginated agent list (`?q=`, `?category=`, `?verified=true`, `?page=`) |
| GET | `/api/agents/<id>` | Single agent |
| GET | `/api/price/<id>` | Live price with surge indicator |
| GET | `/api/search?q=` | AJAX agent search |
| GET | `/api/onchain/info` | Contract addresses + explorer URL |
| GET | `/api/health` | Liveness probe |
| GET | `/api/ready` | Readiness probe (checks DB) |

### On-chain
| Method | Path | Description |
|---|---|---|
| POST | `/api/x402/pay` | Execute EIP-3009 permit → escrow deposit |
| POST | `/api/dispute/submit` | Submit gatekeeper incident |
| GET | `/api/session/<id>` | Read live escrow session from chain |
| POST | `/api/session/<id>/cancel` | Cancel open session |
| GET | `/api/agents/<id>/reputation` | Credit profile from ReputationContract |
| GET | `/api/agents/<id>/stake` | Stake balance from StakingSlashing |

### Auctions
| Method | Path | Description |
|---|---|---|
| GET | `/api/auctions` | Open bids |
| POST | `/api/auctions/bid` | Post open bid on-chain |
| GET | `/api/auctions/<id>` | Bid details |
| POST | `/api/auctions/<id>/cancel` | Cancel bid |

### Seller
| Method | Path | Description |
|---|---|---|
| POST | `/seller/create` | Submit agent listing |
| POST | `/seller/agents/<id>` | Update / pause / reactivate listing |
| POST | `/api/agents/<id>/rate` | Submit buyer rating (1-5) |

### Admin (require `X-Api-Key` header if `API_KEY` is set)
| Method | Path | Description |
|---|---|---|
| POST | `/admin/verification-queue/<id>/approve` | Approve + badge agent |
| POST | `/admin/verification-queue/<id>/reject` | Reject submission |
| POST | `/admin/review/<id>` | Human review decision (approve/reject + notes) |
| POST | `/admin/payouts/<id>/release` | Release seller payout |
| POST | `/admin/moderation/<id>/resolve` | Resolve report |
| POST | `/api/orders/<id>/complete` | Release escrow + mark order complete |

---

## Buyer Flow

1. **Browse** → `/marketplace` → search + filter agents by category, use case, price, verification
2. **Discover** → `/agent/<id>` → see workflow stages, pricing, live price, reviews, on-chain reputation
3. **Checkout** → `/checkout/<id>` → connect wallet, set spend cap, approve sub-agent permissions
4. **Pay** → EIP-3009 permit signed in wallet → backend calls `EscrowPayment.depositFunds`
5. **Track** → `/order/<id>` → live execution progress, real-time cost tracker
6. **Confirm** → "Mark Complete & Release" → calls `POST /api/orders/<id>/complete`
7. **Rate** → 1-5 star rating on the order page after completion

## Seller Flow

1. **List** → `/seller/create` → 4-step wizard: agent info → pricing → verification tier → review
2. **Verify** → choose Basic ($10) or Thorough ($50) audit → submit fee via wallet
3. **Monitor** → `/seller/dashboard` → revenue, orders, verification status
4. **Manage** → `/seller/agents/<id>` → edit, pause, reactivate listing
5. **Earnings** → `/seller/earnings` → revenue chart, surge analytics, transaction history

## Admin / Protocol Flow

1. **Queue** → `/admin/verification-queue` → review pending submissions
2. **Sandbox** → `/admin/sandbox` → automated gate results (static scan, sandbox, gatekeeper AI, fingerprint)
3. **Human Review** → `/admin/review/<id>` → 8-item checklist, notes, approve/reject decision
4. **Moderation** → `/admin/moderation` → reports and complaints
5. **Payouts** → `/admin/payouts` → release or hold seller payments

---

## Verification Tiers

| Tier | Cost | Process | Buyer Badge |
|---|---|---|---|
| **Basic** | $10 USDC | Automated only: static scan, sandbox, gatekeeper AI, model fingerprint | Unverified |
| **Thorough** | $50 USDC | Basic + human protocol team review + ERC-8004 identity registration | ✓ Verified |

All 4 automated security gates must pass within 60 seconds before any listing goes live.

---

## On-chain Payment Flow (x402)

```
Buyer signs EIP-3009 permit (gasless) in MetaMask/Rabby
    ↓
POST /api/x402/pay  (backend facilitator)
    ↓
MockUSDC.transferWithAuthorization()  →  moves USDC to facilitator
MockUSDC.approve(EscrowPayment, amount)
EscrowPayment.depositFunds(agentId, amount, tokenBudget, categoryId, expiresAt)
    ↓
Session ID emitted on-chain → buyer tracks at /order/<sessionId>
    ↓
Agent executes task  →  token usage signed by session key
AgentIdentity.submitTaskCompletion()  →  score ticks up
EscrowPayment.settleSession()  →  seller paid, buyer refunded remainder
```

---

## Post-Hackathon Roadmap

- Replace MockUSDC with real USDC (mainnet USDC on Avalanche C-Chain)
- Open developer registration globally
- Gatekeeper running 24/7 as a managed service
- Flask-Migrate for database schema evolution
- Redis for rate limiter storage (replace in-memory)
- JWT-based user authentication (replace API key)
- Webhook system for order status events
- Real-time WebSocket order tracking (replace polling)
