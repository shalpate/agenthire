"""
sim_engine.py — live, tick-driven agent simulation.

Spawns a daemon thread that advances a simulated clock, generates bid
arrivals, matches them to qualifying agents, settles sessions with realistic
variance, and feeds the reputation / surge / ledger state continuously.

Unlike simulation.py (one-shot historical seed), this runs forever once
started and produces fresh events the UI can tail in real time.

Tick cadence (defaults):
  real 2s  ==  sim 60s   (30× acceleration)
  → one full simulated day ≈ 48 minutes of wall clock.
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from extensions import db
from models import (
    Agent, OnchainProfile, ChainTransaction, PricePoint, AuctionBid,
)
from simulation import (
    compute_surge, SLASH_PCT, SLASH_SPLIT_USER_BPS,
    VOLUME_PER_POINT, MAX_POINTS_PER_TASK, MAX_SCORE,
    DECAY_TARGET, DECAY_PERIOD, _tier_for, _mock_tx_hash,
)


# ── Contract addresses (stable mock set so tx explorer view is consistent) ──

ADDR_STAKING  = "0xfc942b4d1Eb363F25886b3F5935394BD4932B896"
ADDR_ESCROW   = "0xD19990C7CB8C386fa865135Ce9706A5A37A3f2f2"
ADDR_REP      = "0x40ef89Ce1E248Df00AF6Dc37f96BBf92A9Bf603A"
ADDR_AUCTION  = "0x21f4D1c8eA5D8c97e9A95a5B8BD4a54b78F3C6A4"

# Stable category → id mapping so bids can target specific agent types
CATEGORY_IDS = {
    "Development":       0,
    "Data & Analytics":  1,
    "Content":           2,
    "Finance":           3,
    "Research":          4,
    "Security":          5,
    "Automation":        6,
}


def _category_id(agent: Agent) -> int:
    return CATEGORY_IDS.get(agent.category, 6)


@dataclass
class SimEvent:
    id: int
    ts: int           # simulated unix ts
    real_ts: float    # wall clock
    kind: str
    agent_id: int | None
    message: str
    amount_usdc: float = 0.0
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts,
            "realTs": self.real_ts,
            "kind": self.kind,
            "agentId": self.agent_id,
            "message": self.message,
            "amountUSDC": round(self.amount_usdc, 4),
            "meta": self.meta,
        }


class SimulationEngine:
    """Singleton background simulator."""

    def __init__(self, app, *, tick_real_s: float = 2.0, tick_sim_s: int = 60):
        self.app = app
        self.tick_real_s = tick_real_s
        self.tick_sim_s = tick_sim_s
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._event_id = 0
        self.events: deque[SimEvent] = deque(maxlen=500)
        self.started_real_ts = 0.0
        self.sim_clock = int(time.time())
        self.tick_count = 0
        # Per-agent in-flight sessions: [{start_sim_ts, end_sim_ts, tokens, price, deposit, buyer, outcome}]
        self._active: dict[int, list[dict]] = {}
        # Per-agent capacity (concurrent sessions before util saturates)
        self._capacity: dict[int, int] = {}
        # Rolling demand per category for surge
        self._recent_bids: deque[tuple[int, int]] = deque(maxlen=120)  # (sim_ts, category)
        # RNG — fresh each start so sims don't look identical across restarts
        self._rng = random.Random(time.time())

    # ── lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._stop.clear()
            self.started_real_ts = time.time()
            self.sim_clock = int(time.time())
            self._thread = threading.Thread(target=self._run, name="sim-engine", daemon=True)
            self._thread.start()
            self._log_event("system", None, "Simulation engine started")
            return True

    def stop(self) -> bool:
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return False
            self._stop.set()
            self._thread.join(timeout=5)
            self._log_event("system", None, "Simulation engine stopped")
            return True

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> dict:
        return {
            "running": self.is_running(),
            "tickCount": self.tick_count,
            "simClock": self.sim_clock,
            "simClockIso": datetime.fromtimestamp(self.sim_clock, tz=timezone.utc).isoformat(),
            "tickRealSeconds": self.tick_real_s,
            "tickSimSeconds": self.tick_sim_s,
            "acceleration": f"{self.tick_sim_s / self.tick_real_s:.1f}×",
            "activeSessions": sum(len(v) for v in self._active.values()),
            "eventBufferSize": len(self.events),
            "startedRealTs": self.started_real_ts,
        }

    def set_speed(self, tick_real_s: float) -> None:
        self.tick_real_s = max(0.1, min(10.0, float(tick_real_s)))

    def events_since(self, since_id: int = 0, limit: int = 100) -> list[dict]:
        return [e.to_dict() for e in list(self.events)[-limit:] if e.id > since_id]

    # ── main loop ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop.is_set():
            t0 = time.time()
            try:
                with self.app.app_context():
                    self._tick()
                    db.session.commit()
            except Exception as e:
                self.app.logger.exception("sim tick failed: %s", e)
                try:
                    with self.app.app_context():
                        db.session.rollback()
                except Exception:
                    pass
            finally:
                try:
                    with self.app.app_context():
                        db.session.remove()
                except Exception:
                    pass
            elapsed = time.time() - t0
            self._stop.wait(max(0.0, self.tick_real_s - elapsed))

    def _tick(self) -> None:
        self.tick_count += 1
        self.sim_clock += self.tick_sim_s
        agents = Agent.query.all()
        if not agents:
            return

        # 0. Ensure capacity map populated
        for a in agents:
            self._capacity.setdefault(a.id, self._rng.choice([3, 4, 5, 6, 8]))
            self._active.setdefault(a.id, [])

        # 1. Progress in-flight sessions → settle / refund / slash
        self._progress_sessions(agents)

        # 2. Generate new bid arrivals (Poisson)
        self._generate_bids(agents)

        # 3. Match open bids to qualifying agents
        self._match_bids(agents)

        # 4. Demo-driven A2A flow. The natural matching loop rarely picks
        # the 4 flagship composable agents out of 125+ competitors, so we
        # also fire an A2A flow on a flagship every ~10 ticks (~20 real
        # sec) to keep agent-to-agent transactions visible on /sim.
        if self.tick_count % 10 == 0:
            self._fire_demo_a2a_flow()

        # 5. Periodic maintenance
        # Every 5 sim-minutes: snapshot price points
        if self.tick_count % 5 == 0:
            self._snapshot_prices(agents)
        # Every 60 sim-minutes: decay scores + expire stale bids
        if self.tick_count % 60 == 0:
            self._apply_decay(agents)
            self._expire_bids()

    def _fire_demo_a2a_flow(self) -> None:
        """Pick one flagship composable agent and run its A2A sub-agent
        call pattern. Makes agent-to-agent commerce always-visible even
        when the matching lottery doesn't pick flagships naturally."""
        try:
            from app import A2A_WORKFLOWS
        except Exception:
            return
        flagship_ids = list(A2A_WORKFLOWS.keys())
        if not flagship_ids:
            return
        # Shuffle and pick the first non-banned one. Also unban any flagship
        # that got unlucky in the slash lottery — they anchor the A2A story.
        self._rng.shuffle(flagship_ids)
        primary = primary_profile = None
        for candidate_id in flagship_ids:
            a = db.session.get(Agent, candidate_id)
            p = db.session.get(OnchainProfile, candidate_id)
            if not a or not p:
                continue
            if p.banned:
                # Rehabilitate: flagships can't stay banned — the A2A flow
                # needs them. Reset incident count and restore stake.
                p.banned = False
                p.accepting_work = True
                p.stake_incident_count = max(0, p.stake_incident_count - 1)
                p.staked_amount = max(p.staked_amount, 2500 * 1_000_000)
                p.score = max(p.score, 700)
            primary, primary_profile = a, p
            break
        if not primary or not primary_profile:
            return
        # Synth a session so the method has what it needs
        synth_session = {
            "tokens": self._rng.choice([1000, 2000, 5000]),
            "price": primary.min_price,
            "deposit": 0,
            "buyer": "0x" + hashlib.sha256(f"demo-buyer-{self.tick_count}".encode()).hexdigest()[:40],
            "bid_id": f"DEMO-{self.tick_count}",
        }
        tokens_used = int(synth_session["tokens"] * self._rng.uniform(0.8, 1.0))
        # Log a pseudo-settle for the flagship so the A2A flow has upstream context
        self._log_event(
            "settle", primary.id,
            f"{primary.name} settled a {tokens_used}-token job, now routing sub-calls",
            amount=tokens_used * primary.min_price,
            meta={"tokensUsed": tokens_used, "demo": True},
        )
        self._fire_a2a_subagent_calls(primary, primary_profile, tokens_used, synth_session)

    # ── tick sub-steps ────────────────────────────────────────────────────

    def _generate_bids(self, agents) -> int:
        hour = datetime.fromtimestamp(self.sim_clock, tz=timezone.utc).hour
        peak = 9 <= hour < 17
        # Expected arrivals per minute
        lam = 3.5 if peak else 1.0
        n = self._poisson(lam)
        created = 0
        for _ in range(n):
            # Pick the target category first, then price from an agent in that
            # category — keeps bid prices in the right zone for the category.
            a_template = self._rng.choice(agents)
            category = _category_id(a_template)
            tokens = self._rng.choice([250, 500, 1000, 2000, 5000])
            price_ceiling = a_template.min_price * self._rng.uniform(1.05, 1.8)
            deposit = int(tokens * price_ceiling * 1_000_000)
            min_tier = self._rng.choices([1, 2, 3], weights=[70, 22, 8])[0]
            bid = AuctionBid(
                on_chain_bid_id=f"LIVE-{self.tick_count}-{self._event_id + 1}",
                user="0x" + hashlib.sha256(f"bidder-{self.sim_clock}-{self._event_id}".encode()).hexdigest()[:40],
                deposit_amount=deposit,
                token_budget=tokens,
                max_price_per_token=int(price_ceiling * 1_000_000),
                category_id=category,
                min_tier=min_tier,
                expires_at=self.sim_clock + self._rng.choice([5*60, 15*60, 30*60, 2*3600]),
                settled=False, cancelled=False,
            )
            db.session.add(bid)
            self._recent_bids.append((self.sim_clock, category))
            self._log_event(
                "bid_post", None,
                f"New bid {bid.on_chain_bid_id} · {tokens} tokens · T{min_tier}+ · ≤${price_ceiling:.4f}/tok",
                amount=deposit / 1_000_000,
                meta={"bidId": bid.on_chain_bid_id, "tokens": tokens, "minTier": min_tier},
            )
            created += 1
        return created

    def _match_bids(self, agents) -> int:
        open_bids = (
            AuctionBid.query
            .filter_by(settled=False, cancelled=False)
            .filter(AuctionBid.expires_at > self.sim_clock)
            .all()
        )
        matched = 0
        for bid in open_bids:
            # Find qualifying agents: category match, tier gate, accepting, not banned,
            # capacity available, price ceiling respected.
            candidates = []
            for a in agents:
                if _category_id(a) != bid.category_id:
                    continue
                p = db.session.get(OnchainProfile, a.id)
                if not p or p.banned or not p.accepting_work:
                    continue
                if p.tier < bid.min_tier:
                    continue
                if len(self._active[a.id]) >= self._capacity[a.id]:
                    continue
                if int(a.min_price * 1_000_000) > bid.max_price_per_token:
                    continue
                candidates.append((a, p))
            if not candidates:
                continue
            # Clearing rule: highest tier first, then highest reputation, then
            # lowest price. This mirrors how a real buyer would pick among
            # qualified bids — quality before bargain-hunting.
            candidates.sort(key=lambda t: (-t[1].tier, -t[1].score, t[0].min_price))
            agent, profile = candidates[0]
            # Kick off session
            price = agent.min_price * self._rng.uniform(1.0, 1.4)
            if price * 1_000_000 > bid.max_price_per_token:
                price = bid.max_price_per_token / 1_000_000
            deposit = int(bid.token_budget * price * 1_000_000)
            duration = self._rng.randint(90, 600)  # 1.5–10 sim minutes
            # Outcome lottery
            roll = self._rng.random()
            outcome = "settle" if roll < 0.92 else "refund" if roll < 0.97 else "incident"
            session = {
                "start": self.sim_clock,
                "end": self.sim_clock + duration,
                "tokens": bid.token_budget,
                "price": price,
                "deposit": deposit,
                "buyer": bid.user,
                "outcome": outcome,
                "bid_id": bid.on_chain_bid_id,
            }
            self._active[agent.id].append(session)
            # Log deposit tx
            tx_nonce = self._event_id
            db.session.add(ChainTransaction(
                tx_hash=_mock_tx_hash(agent.id, 10_000 + tx_nonce),
                block_number=2_000_000 + self.tick_count * 100 + tx_nonce,
                ts=self.sim_clock,
                kind="deposit",
                agent_id=agent.id,
                from_addr=bid.user,
                to_addr=ADDR_ESCROW,
                amount_usdc=deposit,
                meta=json.dumps({"tokenBudget": bid.token_budget, "pricePerToken": round(price, 6), "bidId": bid.on_chain_bid_id}),
            ))
            bid.settled = True
            bid.tx_hash = _mock_tx_hash(agent.id, 10_000 + tx_nonce)
            self._log_event(
                "bid_claim", agent.id,
                f"{agent.name} claimed {bid.on_chain_bid_id} · {bid.token_budget} tokens @ ${price:.4f}/tok (T{profile.tier})",
                amount=deposit / 1_000_000,
                meta={"bidId": bid.on_chain_bid_id, "duration": duration, "outcome": outcome},
            )
            matched += 1
        return matched

    def _progress_sessions(self, agents) -> None:
        for agent in agents:
            still: list[dict] = []
            profile = db.session.get(OnchainProfile, agent.id)
            if not profile:
                still = self._active[agent.id]
                self._active[agent.id] = still
                continue
            for s in self._active[agent.id]:
                if self.sim_clock < s["end"]:
                    still.append(s)
                    continue
                # Completed — resolve by outcome
                if s["outcome"] == "settle":
                    tokens_used = int(s["tokens"] * self._rng.uniform(0.75, 1.0))
                    paid = int(tokens_used * s["price"] * 1_000_000)
                    refund = s["deposit"] - paid
                    db.session.add(ChainTransaction(
                        tx_hash=_mock_tx_hash(agent.id, 20_000 + self._event_id),
                        block_number=2_000_000 + self.tick_count * 100 + self._event_id,
                        ts=self.sim_clock,
                        kind="settle",
                        agent_id=agent.id,
                        from_addr=ADDR_ESCROW,
                        to_addr=self._wallet_of(profile),
                        amount_usdc=paid,
                        meta=json.dumps({"tokensUsed": tokens_used, "refund": refund, "buyer": s["buyer"], "bidId": s["bid_id"]}),
                    ))
                    # Reputation update
                    points = min(MAX_POINTS_PER_TASK, max(1, paid // VOLUME_PER_POINT))
                    profile.score = min(MAX_SCORE, profile.score + points)
                    profile.tasks_completed += 1
                    # Retier
                    profile.tier = _tier_for(profile.score, profile.tasks_completed)
                    agent.tasks_completed = (agent.tasks_completed or 0) + 1
                    self._log_event(
                        "settle", agent.id,
                        f"{agent.name} settled {tokens_used}/{s['tokens']} tokens · +{points} score → {profile.score} (T{profile.tier})",
                        amount=paid / 1_000_000,
                        meta={"tokensUsed": tokens_used, "score": profile.score, "tier": profile.tier},
                    )
                    # A2A: flagship agents fire sub-agent payments after settling
                    self._fire_a2a_subagent_calls(agent, profile, tokens_used, s)
                elif s["outcome"] == "refund":
                    db.session.add(ChainTransaction(
                        tx_hash=_mock_tx_hash(agent.id, 30_000 + self._event_id),
                        block_number=2_000_000 + self.tick_count * 100 + self._event_id,
                        ts=self.sim_clock,
                        kind="refund",
                        agent_id=agent.id,
                        from_addr=ADDR_ESCROW,
                        to_addr=s["buyer"],
                        amount_usdc=s["deposit"],
                        meta=json.dumps({"reason": "session cancelled", "buyer": s["buyer"]}),
                    ))
                    self._log_event(
                        "refund", agent.id,
                        f"{agent.name} refunded {s['buyer'][:10]}… ({s['tokens']} tokens)",
                        amount=s["deposit"] / 1_000_000,
                    )
                else:  # incident → slash
                    self._do_slash(agent, profile, s)
                    # Refund buyer too
                    db.session.add(ChainTransaction(
                        tx_hash=_mock_tx_hash(agent.id, 40_000 + self._event_id),
                        block_number=2_000_000 + self.tick_count * 100 + self._event_id,
                        ts=self.sim_clock,
                        kind="refund",
                        agent_id=agent.id,
                        from_addr=ADDR_ESCROW,
                        to_addr=s["buyer"],
                        amount_usdc=s["deposit"],
                        meta=json.dumps({"reason": "task failed — slashed", "buyer": s["buyer"]}),
                    ))
            self._active[agent.id] = still

    def _do_slash(self, agent: Agent, profile: OnchainProfile, session: dict) -> None:
        # Flagship composable agents are protected from permanent ban so the
        # A2A story stays intact across long-running demos. They still take
        # the stake + score hit.
        try:
            from app import A2A_WORKFLOWS
            is_flagship = agent.id in A2A_WORKFLOWS
        except Exception:
            is_flagship = False
        profile.stake_incident_count += 1
        idx = min(profile.stake_incident_count, 3) - 1
        pct = SLASH_PCT[idx]
        amount = profile.staked_amount * pct // 100
        profile.staked_amount -= amount
        to_user = amount * SLASH_SPLIT_USER_BPS // 10_000
        if profile.stake_incident_count >= 3 and not is_flagship:
            profile.banned = True
            profile.accepting_work = False
        elif is_flagship and profile.stake_incident_count >= 3:
            # Reset to 2 so one more slash won't immediately re-ban
            profile.stake_incident_count = 2
        # Score penalty
        profile.score = max(0, profile.score - 30)
        profile.rep_incident_count += 1
        profile.tier = _tier_for(profile.score, profile.tasks_completed)
        db.session.add(ChainTransaction(
            tx_hash=_mock_tx_hash(agent.id, 50_000 + self._event_id),
            block_number=2_000_000 + self.tick_count * 100 + self._event_id,
            ts=self.sim_clock,
            kind="slash",
            agent_id=agent.id,
            from_addr=ADDR_REP,
            to_addr=ADDR_STAKING,
            amount_usdc=amount,
            meta=json.dumps({
                "incidentNumber": profile.stake_incident_count,
                "slashPct": pct,
                "toUser": to_user,
                "toInsurance": amount - to_user,
                "banned": profile.banned,
                "buyer": session["buyer"],
            }),
        ))
        banned_tag = " ⚠ BANNED" if profile.banned else ""
        self._log_event(
            "slash", agent.id,
            f"{agent.name} slashed {pct}% · {amount/1_000_000:.2f} USDC · score→{profile.score}{banned_tag}",
            amount=amount / 1_000_000,
            meta={"incidentNumber": profile.stake_incident_count, "banned": profile.banned},
        )

    # ── Agent-to-Agent: a primary agent hires sub-agents after settling ────

    def _fire_a2a_subagent_calls(self, primary_agent: Agent, primary_profile: OnchainProfile,
                                  tokens_used: int, session: dict) -> None:
        """When a composable agent settles its own work, it programmatically
        pays sub-agents per A2A_WORKFLOWS. No human approval; pure agentic
        commerce on Avalanche.

        Each trigger fires:
          - a2a_hire  tx:  primary wallet → escrow (sub-agent deposit)
          - a2a_settle tx: escrow → sub-agent wallet
        Sub-agent's score + task count bump. Primary earns per-call fee split
        by eating it out of its own settle.
        """
        try:
            from app import A2A_WORKFLOWS
        except Exception:
            return
        wf = A2A_WORKFLOWS.get(primary_agent.id)
        if not wf or not wf.get("composable"):
            return
        sub_agents = wf.get("sub_agents", [])
        triggers = wf.get("trigger_rules", [])
        if not sub_agents:
            return

        for trigger in triggers:
            # Each trigger has a `calls` name; resolve to a sub_agent entry
            target_name = trigger.get("calls")
            sub_spec = next((s for s in sub_agents if s.get("name") == target_name), None)
            if not sub_spec:
                continue
            # Fire probability: "Always -..." triggers always fire; others 55%
            always = "always" in (trigger.get("condition") or "").lower()
            if not always and self._rng.random() > 0.55:
                continue

            sub_id = int(sub_spec["id"])
            sub_agent = db.session.get(Agent, sub_id)
            sub_profile = db.session.get(OnchainProfile, sub_id)
            if not sub_agent or not sub_profile or sub_profile.banned:
                continue

            # Fee is a slice of what the primary just billed the user for.
            # Roughly: sub_agent.est_cost_mid * tokens_used
            cost_lo = float(sub_spec.get("est_cost_low", 0.003))
            cost_hi = float(sub_spec.get("est_cost_high", 0.01))
            per_token = self._rng.uniform(cost_lo, cost_hi)
            # For sub-agents billed per-minute, use a fixed 2-3 min engagement
            if sub_spec.get("billing") == "per_minute":
                amount_usdc = per_token * self._rng.uniform(2, 4)
            else:
                amount_usdc = per_token * tokens_used
            amount_micro = int(amount_usdc * 1_000_000)
            if amount_micro <= 0:
                continue

            # Deposit tx: primary agent's wallet sends into escrow
            deposit_hash = _mock_tx_hash(primary_agent.id, 60_000 + self._event_id)
            db.session.add(ChainTransaction(
                tx_hash=deposit_hash,
                block_number=2_000_000 + self.tick_count * 100 + self._event_id,
                ts=self.sim_clock, kind="a2a_hire",
                agent_id=sub_id,
                from_addr=primary_profile.wallet_address,
                to_addr=ADDR_ESCROW,
                amount_usdc=amount_micro,
                meta=json.dumps({
                    "primaryAgentId": primary_agent.id,
                    "primaryAgentName": primary_agent.name,
                    "subAgentName": sub_agent.name,
                    "trigger": trigger.get("condition"),
                    "bidId": session.get("bid_id"),
                }),
            ))
            self._log_event(
                "a2a_hire", primary_agent.id,
                f"{primary_agent.name} → {sub_agent.name} ({trigger.get('condition')})",
                amount=amount_usdc,
                meta={"subAgentId": sub_id, "subAgentName": sub_agent.name,
                      "primaryId": primary_agent.id,
                      "tokens": tokens_used, "billing": sub_spec.get("billing")},
            )

            # Settle tx: sub-agent receives funds, score + task count bump
            settle_hash = _mock_tx_hash(sub_id, 70_000 + self._event_id)
            db.session.add(ChainTransaction(
                tx_hash=settle_hash,
                block_number=2_000_000 + self.tick_count * 100 + self._event_id + 1,
                ts=self.sim_clock, kind="a2a_settle",
                agent_id=sub_id,
                from_addr=ADDR_ESCROW,
                to_addr=sub_profile.wallet_address,
                amount_usdc=amount_micro,
                meta=json.dumps({
                    "primaryAgentId": primary_agent.id,
                    "primaryAgentName": primary_agent.name,
                    "subAgentName": sub_agent.name,
                }),
            ))
            # Rep bump for the sub-agent (smaller than direct-user settles)
            points = min(MAX_POINTS_PER_TASK // 2 or 1,
                         max(1, amount_micro // VOLUME_PER_POINT))
            sub_profile.score = min(MAX_SCORE, sub_profile.score + points)
            sub_profile.tasks_completed += 1
            sub_profile.tier = _tier_for(sub_profile.score, sub_profile.tasks_completed)
            sub_agent.tasks_completed = (sub_agent.tasks_completed or 0) + 1
            self._log_event(
                "a2a_settle", sub_id,
                f"{sub_agent.name} got paid by {primary_agent.name} · +{points} score → {sub_profile.score}",
                amount=amount_usdc,
                meta={"primaryId": primary_agent.id,
                      "primaryName": primary_agent.name,
                      "score": sub_profile.score, "tier": sub_profile.tier},
            )

    def _snapshot_prices(self, agents) -> None:
        for a in agents:
            util = min(1.0, len(self._active[a.id]) / max(1, self._capacity[a.id]))
            # Demand ≈ recent bids in the last 15 sim-min / 15 (rough normalization)
            cutoff = self.sim_clock - 15 * 60
            recent = sum(1 for t, _ in self._recent_bids if t >= cutoff)
            demand = min(1.0, recent / 15.0)
            now_dt = datetime.fromtimestamp(self.sim_clock, tz=timezone.utc)
            surge = compute_surge(util, demand, now_dt)
            price = round(a.min_price * surge, 6)
            if price > a.max_price:
                price = a.max_price
            db.session.add(PricePoint(
                agent_id=a.id, ts=self.sim_clock,
                price_per_token=price, utilization=round(util, 3), surge=surge,
            ))
            # Also persist onto Agent row so /marketplace shows live surge.
            # Surging means this specific agent is actually in demand, not
            # that UTC peak hours are adding a flat time-of-day bonus.
            a.current_price = price
            a.surge_multiplier = surge
            a.surge_active = (util > 0.5 or demand > 0.5) and surge > 1.2

    def _apply_decay(self, agents) -> None:
        for a in agents:
            p = db.session.get(OnchainProfile, a.id)
            if not p:
                continue
            elapsed = self.sim_clock - (p.last_decay_ts or self.sim_clock)
            periods = elapsed // DECAY_PERIOD
            if not periods:
                continue
            if p.score > DECAY_TARGET:
                p.score = max(DECAY_TARGET, p.score - int(periods))
            elif p.score < DECAY_TARGET:
                p.score = min(DECAY_TARGET, p.score + int(periods))
            p.last_decay_ts = self.sim_clock
            p.tier = _tier_for(p.score, p.tasks_completed)

    def _expire_bids(self) -> None:
        stale = (
            AuctionBid.query
            .filter_by(settled=False, cancelled=False)
            .filter(AuctionBid.expires_at <= self.sim_clock)
            .all()
        )
        for b in stale:
            b.cancelled = True
            self._log_event(
                "bid_cancel", None,
                f"Bid {b.on_chain_bid_id} expired unmatched",
                meta={"bidId": b.on_chain_bid_id},
            )

    # ── helpers ───────────────────────────────────────────────────────────

    def _poisson(self, lam: float) -> int:
        L = 2.718281828 ** -lam
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= self._rng.random()
            if p <= L:
                return k - 1

    def _wallet_of(self, profile: OnchainProfile) -> str:
        return profile.wallet_address

    def _log_event(self, kind: str, agent_id: int | None, message: str, *, amount: float = 0.0, meta: dict | None = None) -> None:
        self._event_id += 1
        ev = SimEvent(
            id=self._event_id, ts=self.sim_clock, real_ts=time.time(),
            kind=kind, agent_id=agent_id, message=message,
            amount_usdc=amount, meta=meta or {},
        )
        self.events.append(ev)


# ── module-level singleton accessor ──────────────────────────────────────────

_engine: SimulationEngine | None = None


def get_engine(app=None) -> SimulationEngine:
    global _engine
    if _engine is None:
        if app is None:
            raise RuntimeError("Engine not initialized — call get_engine(app) first")
        _engine = SimulationEngine(app)
    return _engine
