# AgentHire — Full-Stack Integration Guide

How the frontend (this repo) connects to the on-chain layer.

## Stack overview

```
┌──────────────────┐    ┌───────────────┐    ┌───────────────────────────┐
│  Browser + Wallet│◄──►│  Flask (this) │◄──►│  Node services (separate) │
│  (ethers + 3009) │    │  mock data +  │    │  facilitator + gatekeeper │
│                  │    │  proxy APIs   │    │                           │
└──────────────────┘    └───────────────┘    └───────────────┬───────────┘
                                                             │
                                                             ▼
                                              ┌──────────────────────────┐
                                              │   Avalanche Fuji L1      │
                                              │   6 smart contracts      │
                                              └──────────────────────────┘
```

## Deployed contracts (Fuji, chainId 43113)

| Contract | Address |
|---|---|
| MockUSDC (EIP-3009 enabled) | `0x9C49D730Dfb82B7663aBE6069B5bFe867fa34c9f` |
| AgentRegistry | `0x6B71b84Fa3C313ccC43D63A400Ab47e6A0d4BCbB` |
| ReputationContract | `0x40ef89Ce1E248Df00AF6Dc37f96BBf92A9Bf603A` |
| StakingSlashing | `0xfc942b4d1Eb363F25886b3F5935394BD4932B896` |
| EscrowPayment | `0xD19990C7CB8C386fa865135Ce9706A5A37A3f2f2` |
| AuctionMarket | `0xa7AEEca5a76bd5Cd38B15dfcC2c288d3645E53E3` |

All verified on Snowtrace. ABIs + signer helpers live in the contract repo (`ai-agent-marketplace/abi/`).

## Frontend API (this repo)

### Global: `window.AgentHire`

Loaded by `static/js/web3.js`. Always present after DOMContentLoaded.

| Method | What it does |
|---|---|
| `connectWallet()` | Prompts wallet, auto-switches to Fuji, stores signer |
| `getUsdcBalance()` | Current wallet USDC balance (6-dec base units) |
| `mintUSDC(n)` | Testnet faucet — mints n USDC to connected wallet |
| `getAgentProfile(id)` | One-call read: agent + listing + reputation + stake |
| `payWithX402({ agentId, depositUSDC, tokenBudget, facilitator })` | Sign EIP-3009 permit → POST `/api/x402/pay` → returns session id |
| `depositDirect({ ... })` | Fallback: `approve` + `depositFunds` (two transactions) |

### Flask endpoints (proxies to Node services)

| Route | Purpose |
|---|---|
| `GET /api/onchain/info` | All contract addresses + explorer URL |
| `POST /api/x402/pay` | Forwards signed permit to `FACILITATOR_URL` |
| `GET /api/session/<id>` | Reads live escrow session from chain |
| `POST /api/dispute/submit` | Forwards dispute to `GATEKEEPER_URL` |

## Running the full stack locally

### 1. Start the on-chain services (Node)

From the `ai-agent-marketplace` repo:

```bash
# Terminal 1 — facilitator (handles x402 payments)
cd ai-agent-marketplace
AGENT_PRIVATE_KEY=0x... \
FACILITATOR_PRIVATE_KEY=0x... \
PORT=3000 \
node backend-ref/example-agent-server.js

# Terminal 2 — gatekeeper (signs incidents for disputes)
GATEKEEPER_PRIVATE_KEY=0x... \
PORT=3001 \
node backend-ref/gatekeeper-server.js
```

The gatekeeper key MUST match the one set at contract deploy time:
`0xdb4135c6884D81497769440788306EE985DD1A6e`. Hit `http://localhost:3001/health` to verify.

### 2. Start Flask with proxy env

```bash
# Terminal 3
cd agenthire
FACILITATOR_URL=http://localhost:3000 \
GATEKEEPER_URL=http://localhost:3001 \
python app.py
```

### 3. Open browser

http://localhost:5000 — everything works end-to-end on live Fuji.

## Demo flows

### x402 payment
1. Browse to `/checkout/1`
2. Click "Confirm & Pay in Escrow"
3. Wallet prompts you to sign an EIP-712 `TransferWithAuthorization`
4. Frontend POSTs the signed permit to Flask → Flask forwards to Node facilitator
5. Facilitator submits 3 txs atomically:
   - `MockUSDC.transferWithAuthorization` (pulls USDC from you, pays gas)
   - `MockUSDC.approve(escrow, value)`
   - `EscrowPayment.depositFunds(...)` (opens session)
6. Returns session id → frontend redirects to order page

### Live session display
1. After checkout, `/order/<sessionId>` loads
2. If session id is numeric, frontend calls `/api/session/<id>` → Flask → Node → `EscrowPayment.getSession`
3. Renders a panel showing deposit, price/token, state, expiry

### Seller staking
1. Go to `/seller/dashboard`
2. "On-chain stake" card auto-loads current stake
3. Enter amount → "Stake USDC" signs tx directly (not via facilitator — staker is msg.sender)

### Dispute
1. Go to `/order/<id>`
2. Click "Open Dispute" in the right column
3. Enter reason + severity
4. POSTs to `/api/dispute/submit` → Flask → gatekeeper service
5. Gatekeeper signs + submits `ReputationContract.submitIncident(agentId, affectedUser, severity, sig)`
6. For severity=2, the contract cascades to `StakingSlashing.slash(agentId, affectedUser)` — 60/40 distribution

### Auction
1. Go to `/marketplace`
2. Click floating "⚡ Post Open Bid"
3. Modal collects deposit, budget, ceiling, minTier
4. Directly signs `AuctionMarket.postBid(...)` from the connected wallet

### Live feed
Home page (`/`) shows "LIVE ON-CHAIN ACTIVITY" — polls 6 event types every 12 seconds from the three markets. Click any event to open its tx on Snowtrace.

## Mock fallback

All 3 proxy routes fall back to mock responses if the corresponding Node service is not configured:

| Missing env | Behavior |
|---|---|
| `FACILITATOR_URL` unset | `/api/x402/pay` returns a fake session id |
| `GATEKEEPER_URL` unset | `/api/dispute/submit` returns `pending_review` (no on-chain tx) |

This lets the UI be demo'd without the full backend running. For the bounty judges, wire everything and show real on-chain txs.

## Bounty rubric mapping

| Requirement | Where |
|---|---|
| Settlement on Avalanche C-Chain | Fuji testnet, 6 contracts verified on Snowtrace |
| x402 for pay-per-request | `static/js/web3.js::payWithX402` + facilitator `POST /x402/execute` |
| ERC-8004 identity + reputation | `ReputationContract.getCreditProfile`, `getCategoryTier`, `IERC8004.sol` interface shim |
| Triggered programmatically | Facilitator auto-submits `transferWithAuthorization` → `depositFunds`; token counter auto-signs settlement |
| Gated by on-chain reputation | `EscrowPayment.depositFunds` enforces tier cap; `AuctionMarket.claimBid` enforces `minTier` |
| Cross-service composition | Escrow ↔ Auction both call Reputation.recordCompletion; Reputation ↔ Staking; Staking ↔ Registry |
