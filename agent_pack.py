"""
agent_pack.py — realistic, category-specific roster generator.

Generates a seeded, deterministic set of 10–20 agents per category so the
marketplace has enough depth to feel real. Writes directly to the Agent
table, then lets simulation.seed_simulation() attach OnchainProfiles.

Safe to re-run: only inserts agents whose (name) isn't already in the DB.
"""
from __future__ import annotations
import hashlib
import json
import random
from datetime import datetime, timezone

from extensions import db
from models import Agent


# ── Curated name banks per category ──────────────────────────────────────────

CATEGORY_AGENT_TEMPLATES = {
    "Development": {
        "names": [
            "RefactorPilot", "CommitGuardian", "SnakeLint", "KotlinForge", "RustSentinel",
            "PyDocHero", "JavaScriptJedi", "GoPathfinder", "GitMerge AI", "APIStitcher",
            "DepResolver", "BranchBuddy", "TestSmith", "CodeCartographer", "StackTracer",
            "MonorepoMate", "SchemaShaper", "MigrationMapper",
        ],
        "tags_pool": ["python", "javascript", "typescript", "rust", "go", "linting",
                      "refactor", "git", "ci", "testing", "documentation", "api"],
        "capabilities": [
            "Static code analysis", "Automated refactoring", "Test generation",
            "API contract verification", "Dependency audit", "Merge conflict resolution",
        ],
        "use_cases": ["Code Review", "Testing"],
        "price_range": (0.002, 0.015),
        "billing_mix": ["per_token"] * 8 + ["per_minute"] * 2,
    },
    "Data & Analytics": {
        "names": [
            "QuerySage", "DashboardDruid", "ETL Alchemist", "SnowflakeSeer", "MetricMiner",
            "PivotPro", "ColumnCrafter", "CohortCarver", "ChartChampion", "SQL Sherpa",
            "DataDiff", "SchemaSketcher", "BigQueryButler", "KPI Keeper", "TableauTamer",
            "DWH Detective",
        ],
        "tags_pool": ["sql", "analytics", "dashboard", "etl", "bigquery", "snowflake",
                      "postgres", "visualization", "kpi", "cohort"],
        "capabilities": [
            "Complex SQL generation", "Dashboard scaffolding", "Cohort analysis",
            "ETL pipeline design", "Anomaly detection", "Report automation",
        ],
        "use_cases": ["Data Processing", "Reports"],
        "price_range": (0.005, 0.08),
        "billing_mix": ["per_token"] * 6 + ["per_minute"] * 4,
    },
    "Content": {
        "names": [
            "BlogBard", "ScriptScribe", "HeadlineHeroes", "SEOScribe", "NewsletterNinja",
            "BrandVoice AI", "CaptionCraft", "PressPilot", "WhitepaperWeaver", "SlideSmith",
            "EmailEcho", "ThreadTailor", "PodcastPen", "StoryStitcher", "MicrocopyMuse",
        ],
        "tags_pool": ["writing", "seo", "copywriting", "blog", "newsletter", "social",
                      "email", "marketing", "content"],
        "capabilities": [
            "Long-form blog posts", "SEO-optimized landing copy", "Email sequences",
            "Social threads", "Brand voice matching", "Byline ghostwriting",
        ],
        "use_cases": ["Content Generation"],
        "price_range": (0.001, 0.006),
        "billing_mix": ["per_token"] * 9 + ["per_minute"],
    },
    "Finance": {
        "names": [
            "ArbHunter", "PortfolioPilot", "OnChainOracle", "DeFi Navigator", "TaxTamer",
            "CreditScorer", "YieldSage", "RiskRadar", "TreasuryTracker", "LedgerLens",
            "OptionsOwl", "MarketMuse", "WalletWarden", "StablecoinScout", "EquityEagle",
            "MACD Maestro", "BacktestBaron",
        ],
        "tags_pool": ["defi", "trading", "portfolio", "tax", "risk", "derivatives",
                      "options", "yield", "backtesting", "macro"],
        "capabilities": [
            "Portfolio risk analysis", "On-chain transaction tracing", "Tax lot reconciliation",
            "Yield strategy comparison", "Options pricing", "Backtest generation",
        ],
        "use_cases": ["Trading", "Analysis"],
        "price_range": (0.02, 0.6),
        "billing_mix": ["per_token"] * 4 + ["per_minute"] * 6,
    },
    "Research": {
        "names": [
            "PaperPilot", "CitationCompass", "LitReview AI", "ArxivArchivist",
            "MetaAnalyst", "QuoteQuarry", "SourceSleuth", "AbstractArtisan",
            "HypoHelper", "ReferenceRanger", "DataDigger", "FactForager",
            "NotebookNavigator", "ThesisTethys",
        ],
        "tags_pool": ["research", "papers", "citations", "academic", "literature",
                      "meta-analysis", "arxiv", "pubmed"],
        "capabilities": [
            "Lit review synthesis", "Citation graph traversal", "Paper summarization",
            "Meta-analysis assistance", "Source verification", "Claim checking",
        ],
        "use_cases": ["Research", "Summarization"],
        "price_range": (0.003, 0.04),
        "billing_mix": ["per_token"] * 7 + ["per_minute"] * 3,
    },
    "Security": {
        "names": [
            "VulnVector", "PentestPal", "CVEHunter", "ThreatWeaver", "ZeroDayZealot",
            "PhishFinder", "SecretSweeper", "AuthAudit AI", "RBAC Ranger", "OWASPOracle",
            "SCAScout", "CryptoReviewer", "ForensicsForge", "IRCopilot", "SOC Sentinel",
            "RedTeamRover",
        ],
        "tags_pool": ["security", "pentest", "audit", "owasp", "cve", "forensics",
                      "threat-model", "vulnerabilities", "incident-response"],
        "capabilities": [
            "OWASP Top-10 scan", "Dependency CVE audit", "Threat modeling",
            "Secret detection", "Auth/RBAC review", "Smart contract audit",
        ],
        "use_cases": ["Security Audit"],
        "price_range": (0.005, 0.05),
        "billing_mix": ["per_token"] * 5 + ["per_minute"] * 5,
    },
    "Automation": {
        "names": [
            "WorkflowWiz", "ZapierZen", "CronConductor", "InboxIngestor", "SheetSorcerer",
            "ScrapeSmith", "RPA Rover", "WebhookWrangler", "FormFiller", "CalendarCopilot",
            "DocuSignScribe", "SlackBotSmith", "PipelinePilot", "NotionNavigator",
            "AirtableAce",
        ],
        "tags_pool": ["automation", "workflow", "scraping", "rpa", "webhook",
                      "integration", "zapier", "no-code"],
        "capabilities": [
            "Cross-service workflow orchestration", "Headless browser scraping",
            "Form auto-fill", "Calendar coordination", "Webhook routing", "Sheet macros",
        ],
        "use_cases": ["Automation"],
        "price_range": (0.001, 0.02),
        "billing_mix": ["per_token"] * 6 + ["per_minute"] * 4,
    },
}


SELLERS = [
    "0xAgentWorks Labs", "Catalyst AI", "ForgeOps", "MercuryAI",
    "Opentensor Studio", "Prism Labs", "Synapse Co", "Vertex AI Collective",
    "Runway Research", "Helix Agents",
]


def _seller_wallet(seller: str, i: int) -> str:
    return "0x" + hashlib.sha256(f"{seller}-{i}".encode()).hexdigest()[:40]


def build_agents(seed: int = 42) -> list[dict]:
    """Build a deterministic roster of 10-20 agents per category."""
    rng = random.Random(seed)
    roster: list[dict] = []

    for category, tpl in CATEGORY_AGENT_TEMPLATES.items():
        # Count is deterministic per category (seed makes it reproducible)
        count = rng.randint(10, 20)
        # Take the first `count` names, shuffled a bit
        names = list(tpl["names"])
        rng.shuffle(names)
        names = names[:count]

        for name in names:
            # Price band within category
            lo, hi = tpl["price_range"]
            min_p = round(rng.uniform(lo, (lo + hi) / 2), 5)
            max_p = round(rng.uniform(min_p * 2, hi), 5)

            billing = rng.choice(tpl["billing_mix"])
            rating = round(rng.uniform(3.9, 4.95), 1)
            reviews = rng.randint(12, 2400)
            tasks = rng.randint(200, 25_000)
            tags = rng.sample(tpl["tags_pool"], k=min(len(tpl["tags_pool"]), rng.randint(3, 5)))
            caps = rng.sample(tpl["capabilities"], k=min(len(tpl["capabilities"]), rng.randint(3, 5)))
            use_case = rng.choice(tpl["use_cases"])
            seller = rng.choice(SELLERS)

            # Verification status — most are verified, some pending
            verified_roll = rng.random()
            if verified_roll > 0.25:
                verified = True
                tier = rng.choices(["basic", "advanced", "premium"], weights=[50, 35, 15])[0]
            else:
                verified = False
                tier = "none"

            # Surge state
            surge_on = rng.random() < 0.35
            surge_mult = round(rng.uniform(1.1, 2.2), 2) if surge_on else 1.0
            cur_price = round(min_p * surge_mult, 6)
            if cur_price > max_p:
                cur_price = max_p

            roster.append({
                "name": name,
                "description": f"{use_case} specialist — {caps[0].lower()} and more.",
                "long_description": (
                    f"{name} is a production-grade {category.lower()} agent specializing in "
                    f"{use_case.lower()}. Strengths: {', '.join(caps[:3]).lower()}."
                ),
                "category": category,
                "use_case": use_case,
                "verified": verified,
                "verification_tier": tier,
                "featured": rng.random() < 0.1,
                "rating": rating,
                "reviews": reviews,
                "billing": billing,
                "min_price": min_p,
                "max_price": max_p,
                "current_price": cur_price,
                "surge_active": surge_on,
                "surge_multiplier": surge_mult,
                "seller": seller,
                "seller_rating": round(rng.uniform(4.2, 5.0), 1),
                "tasks_completed": tasks,
                "avg_completion_time": rng.choice(["30 sec", "1 min", "2 min", "4 min", "7 min", "15 min"]),
                "tags": tags,
                "capabilities": caps,
            })
    return roster


def seed_bulk_agents(app) -> int:
    """Insert any missing agents from the pack. Returns number created."""
    created = 0
    with app.app_context():
        existing_names = {a.name for a in Agent.query.all()}
        for spec in build_agents():
            if spec["name"] in existing_names:
                continue
            row = Agent(
                name=spec["name"], description=spec["description"],
                long_description=spec["long_description"],
                category=spec["category"], use_case=spec["use_case"],
                verified=spec["verified"], verification_tier=spec["verification_tier"],
                featured=spec["featured"], rating=spec["rating"], reviews=spec["reviews"],
                billing=spec["billing"], min_price=spec["min_price"], max_price=spec["max_price"],
                current_price=spec["current_price"], surge_active=spec["surge_active"],
                surge_multiplier=spec["surge_multiplier"], seller=spec["seller"],
                seller_rating=spec["seller_rating"], tasks_completed=spec["tasks_completed"],
                avg_completion_time=spec["avg_completion_time"],
            )
            row.tags = spec["tags"]
            row.capabilities = spec["capabilities"]
            db.session.add(row)
            created += 1
        db.session.commit()
        app.logger.info("Bulk roster seeded: %d new agents across %d categories.",
                        created, len(CATEGORY_AGENT_TEMPLATES))
    return created
