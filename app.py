from flask import Flask, render_template, request, jsonify, redirect, url_for
import logging
import os
import random
import time

from config import config as _config_map
from extensions import db, cors, limiter
from auth import require_api_key

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("agenthire")

# ── App factory ────────────────────────────────────────────────────────────────
app = Flask(__name__)

_env = os.environ.get("FLASK_ENV", "development")
app.config.from_object(_config_map.get(_env, _config_map["default"]))

# Init extensions
db.init_app(app)
cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})
limiter.init_app(app)

app.jinja_env.globals['enumerate'] = enumerate

# Request logging
@app.before_request
def _log_request():
    log.info("%s %s", request.method, request.path)

@app.after_request
def _log_response(response):
    log.info("%s %s → %s", request.method, request.path, response.status_code)
    return response

# ── Mock Data ──────────────────────────────────────────────────────────────────

CATEGORIES = ["Development", "Data & Analytics", "Content", "Finance", "Research", "Security", "Automation"]
USE_CASES  = ["Code Review", "Translation", "Summarization", "Trading", "Web Scraping", "Image Generation", "Testing", "Resume & Career"]

# ── A2A Workflow definitions ────────────────────────────────────────────────────
A2A_WORKFLOWS = {
    1: {  # CodeReview Pro
        "composable": True,
        "stage_count": 4,
        "workflow_label": "4-stage analysis pipeline",
        "workflow_summary": "Analyzes code → routes to SecureAudit AI if vulnerabilities detected → routes to TestingMaster if coverage gaps found → compiles unified report.",
        "trigger_rules": [
            {"condition": "Security issues detected", "calls": "SecureAudit AI", "trigger": "automatic"},
            {"condition": "Test coverage < 80%",      "calls": "TestingMaster",  "trigger": "automatic"},
        ],
        "sub_agents": [
            {"id": 7,  "name": "SecureAudit AI", "role": "Deep vulnerability scan",   "billing": "per_token", "est_cost_low": 0.003, "est_cost_high": 0.012, "verified": True},
            {"id": 10, "name": "TestingMaster",  "role": "Test suite generation",     "billing": "per_token", "est_cost_low": 0.002, "est_cost_high": 0.006, "verified": True},
        ],
        "base_cost_label":      "$0.00600 / token",
        "subagent_range_label": "$0.003 - $0.018",
        "total_range_label":    "$0.009 - $0.024",
        "steps": [
            {"name": "CodeReview Pro",  "role": "main",      "action": "Parse & analyse source code"},
            {"name": "SecureAudit AI",  "role": "subagent",  "action": "Deep vulnerability scan (if needed)"},
            {"name": "TestingMaster",   "role": "subagent",  "action": "Generate test coverage report (if needed)"},
            {"name": "CodeReview Pro",  "role": "main",      "action": "Compile unified findings report"},
        ],
        "stages": [
            {
                "id": "parse",    "order": 1, "type": "internal",  "conditional": False,
                "name": "Input Parser",
                "exec_label": "Parsing your code",
                "purpose": "Tokenises submitted code, detects language and framework, maps the dependency graph.",
                "detail": "Supports 20+ languages. Normalises whitespace, strips comments for analysis, extracts AST structure for downstream stages.",
                "summary": "Parsed your code - detected Python, 14 files, 2,840 tokens.",
            },
            {
                "id": "reason",   "order": 2, "type": "internal",  "conditional": False,
                "name": "Reasoning Engine",
                "exec_label": "Analysing code patterns",
                "purpose": "Applies OWASP rules, static analysis heuristics, and pattern matching against known vulnerability signatures.",
                "detail": "Checks 300+ rule patterns. Scores each finding by severity (Critical / High / Med / Low). Flags code paths for sub-agent escalation.",
                "summary": "Found 3 potential issues - escalating 2 for deep scan.",
            },
            {
                "id": "secure",   "order": 3, "type": "subagent",  "conditional": True,
                "name": "SecureAudit AI",
                "exec_label": "Running deep vulnerability scan",
                "purpose": "Sub-agent. Runs CVE database matching and smart contract safety checks when security issues are flagged.",
                "detail": "Called only if Reasoning Engine flags security-severity findings. Adds 15-90s to execution time. Billed separately.",
                "summary": "Confirmed 2 high-severity vulnerabilities - SQL injection (line 142), unvalidated auth input.",
            },
            {
                "id": "format",   "order": 4, "type": "internal",  "conditional": False,
                "name": "Output Formatter",
                "exec_label": "Compiling your report",
                "purpose": "Structures findings into a prioritised report with severity ratings, code snippets, and remediation steps.",
                "detail": "Outputs: executive summary, per-issue breakdown, diff-ready patches, and a machine-readable JSON manifest.",
                "summary": "Report compiled - 3 issues, 2 high, 1 medium. PDF and JSON available.",
            },
        ],
    },
    4: {  # AlphaTrader AI
        "composable": True,
        "stage_count": 4,
        "workflow_label": "4-stage signal pipeline",
        "workflow_summary": "Ingests market data → calls ResearchBot Pro for macro context → calls FinanceGPT for portfolio modeling → generates final signal set.",
        "trigger_rules": [
            {"condition": "Always - macro context required", "calls": "ResearchBot Pro", "trigger": "automatic"},
            {"condition": "Portfolio analysis requested",    "calls": "FinanceGPT",      "trigger": "automatic"},
        ],
        "sub_agents": [
            {"id": 6,  "name": "ResearchBot Pro", "role": "Market & macro research",   "billing": "per_token", "est_cost_low": 0.02, "est_cost_high": 0.08, "verified": True},
            {"id": 11, "name": "FinanceGPT",      "role": "Portfolio & DCF modeling",  "billing": "per_minute","est_cost_low": 0.10, "est_cost_high": 0.25, "verified": True},
        ],
        "base_cost_label":      "$0.45000 / min",
        "subagent_range_label": "$0.12 - $0.33",
        "total_range_label":    "$0.57 - $0.78 / min",
        "steps": [
            {"name": "AlphaTrader AI",  "role": "main",     "action": "Ingest live market data & price history"},
            {"name": "ResearchBot Pro", "role": "subagent", "action": "Pull macro research & news context"},
            {"name": "FinanceGPT",      "role": "subagent", "action": "Portfolio correlation & risk modeling"},
            {"name": "AlphaTrader AI",  "role": "main",     "action": "Generate final buy/sell signals"},
        ],
        "stages": [
            {
                "id": "ingest",   "order": 1, "type": "internal",  "conditional": False,
                "name": "Market Data Ingestion",
                "exec_label": "Fetching live market data",
                "purpose": "Pulls OHLCV data, order book depth, and funding rates from connected exchanges.",
                "detail": "Aggregates across 12 exchange feeds. Normalises tick data to 1-min candles. Detects data gaps and fills via interpolation.",
                "summary": "Ingested 90 days of BTC/ETH data - 129,600 candles across 3 exchanges.",
            },
            {
                "id": "research", "order": 2, "type": "subagent",  "conditional": False,
                "name": "ResearchBot Pro",
                "exec_label": "Gathering macro research",
                "purpose": "Sub-agent. Always called - provides macro context, news sentiment, and on-chain metrics.",
                "detail": "Queries 40+ news sources and on-chain analytics. Outputs a sentiment score and key macro flags that feed the signal model.",
                "summary": "Macro: bearish sentiment (score −0.34). Key flag: Fed rate decision in 3 days.",
            },
            {
                "id": "model",    "order": 3, "type": "subagent",  "conditional": True,
                "name": "FinanceGPT",
                "exec_label": "Running portfolio model",
                "purpose": "Sub-agent. Called when portfolio analysis is requested. Runs DCF and correlation analysis.",
                "detail": "Builds a correlation matrix across your holdings, runs Monte Carlo simulation (10k paths), outputs VaR at 95% and 99% confidence.",
                "summary": "Portfolio VaR (95%): $1,240. Correlation risk: BTC/ETH at 0.87 - consider hedging.",
            },
            {
                "id": "signal",   "order": 4, "type": "internal",  "conditional": False,
                "name": "Signal Generator",
                "exec_label": "Generating trade signals",
                "purpose": "Combines market data, macro context, and portfolio state to produce final buy/sell signals with confidence scores.",
                "detail": "Ensemble of LSTM, momentum, and mean-reversion models. Each signal includes entry price, stop-loss, take-profit, and confidence %.",
                "summary": "Generated 4 signals - 2 long BTC, 1 short ETH, 1 hold. Avg confidence: 73%.",
            },
        ],
    },
    3: {  # DataSift Analytics
        "composable": True,
        "stage_count": 4,
        "workflow_label": "4-stage analytics pipeline",
        "workflow_summary": "Evaluates data source → calls WebCrawler X if external data needed → calls ResearchBot for domain context → runs analysis pipeline.",
        "trigger_rules": [
            {"condition": "External data source required", "calls": "WebCrawler X",   "trigger": "automatic"},
            {"condition": "Domain context needed",         "calls": "ResearchBot Pro","trigger": "automatic"},
        ],
        "sub_agents": [
            {"id": 5, "name": "WebCrawler X",    "role": "External data acquisition", "billing": "per_minute","est_cost_low": 0.02, "est_cost_high": 0.06, "verified": False},
            {"id": 6, "name": "ResearchBot Pro", "role": "Domain knowledge context",  "billing": "per_token", "est_cost_low": 0.01, "est_cost_high": 0.03, "verified": True},
        ],
        "base_cost_label":      "$0.18000 / min",
        "subagent_range_label": "$0.03 - $0.09",
        "total_range_label":    "$0.21 - $0.27 / min",
        "steps": [
            {"name": "DataSift Analytics", "role": "main",     "action": "Evaluate data source & task scope"},
            {"name": "WebCrawler X",       "role": "subagent", "action": "Acquire external data (if needed)"},
            {"name": "ResearchBot Pro",    "role": "subagent", "action": "Provide domain context (if needed)"},
            {"name": "DataSift Analytics", "role": "main",     "action": "Run analysis pipeline & generate report"},
        ],
        "stages": [
            {
                "id": "eval",     "order": 1, "type": "internal",  "conditional": False,
                "name": "Source Evaluator",
                "exec_label": "Evaluating your data source",
                "purpose": "Assesses the data source - CSV, endpoint, or database - and determines if external acquisition is needed.",
                "detail": "Validates schema, detects column types, checks for nulls and outliers. Determines if external enrichment is required.",
                "summary": "Loaded Q1 sales CSV - 48,200 rows, 12 columns, 3.2% null rate detected.",
            },
            {
                "id": "crawl",    "order": 2, "type": "subagent",  "conditional": True,
                "name": "WebCrawler X",
                "exec_label": "Acquiring external data",
                "purpose": "Sub-agent. Fetches external data when the source requires web enrichment.",
                "detail": "Renders JS pages, handles pagination and rate limiting. Outputs structured JSON ready for merge with your dataset.",
                "summary": "Scraped 240 competitor pricing records - merged with your dataset.",
            },
            {
                "id": "context",  "order": 3, "type": "subagent",  "conditional": True,
                "name": "ResearchBot Pro",
                "exec_label": "Gathering domain context",
                "purpose": "Sub-agent. Provides industry benchmarks and domain knowledge to interpret your data accurately.",
                "detail": "Queries industry reports and publishes domain averages. Outputs a context layer that improves anomaly detection accuracy.",
                "summary": "Added retail sector benchmarks - identified 14% above-average churn signal.",
            },
            {
                "id": "analyse",  "order": 4, "type": "internal",  "conditional": False,
                "name": "Analysis Engine",
                "exec_label": "Running analysis pipeline",
                "purpose": "Runs statistical modelling, anomaly detection, and chart generation on the combined dataset.",
                "detail": "Applies EDA, regression, clustering (k-means), and time-series decomposition. Outputs executive summary + downloadable charts.",
                "summary": "Analysis complete - 6 key insights, 3 anomalies flagged, 8 charts generated.",
            },
        ],
    },
    7: {  # SecureAudit AI
        "composable": True,
        "stage_count": 4,
        "workflow_label": "4-stage security audit",
        "workflow_summary": "Runs static analysis via CodeReview Pro first → performs deep security scan → generates prioritised vulnerability report.",
        "trigger_rules": [
            {"condition": "Always - static analysis required first", "calls": "CodeReview Pro", "trigger": "automatic"},
        ],
        "sub_agents": [
            {"id": 1, "name": "CodeReview Pro", "role": "Initial static analysis pass", "billing": "per_token", "est_cost_low": 0.004, "est_cost_high": 0.010, "verified": True},
        ],
        "base_cost_label":      "$0.01500 / token",
        "subagent_range_label": "$0.004 - $0.010",
        "total_range_label":    "$0.019 - $0.025",
        "steps": [
            {"name": "SecureAudit AI",  "role": "main",     "action": "Parse contract / infrastructure config"},
            {"name": "CodeReview Pro",  "role": "subagent", "action": "Static analysis & code quality pass"},
            {"name": "SecureAudit AI",  "role": "main",     "action": "Deep vulnerability scan & CVE matching"},
            {"name": "SecureAudit AI",  "role": "main",     "action": "Compile prioritised remediation report"},
        ],
        "stages": [
            {
                "id": "parse",    "order": 1, "type": "internal",  "conditional": False,
                "name": "Contract Parser",
                "exec_label": "Parsing your contract",
                "purpose": "Parses Solidity, Vyper, or infrastructure config files and builds an annotated control-flow graph.",
                "detail": "Detects compiler version, pragma settings, inheritance chains, and external call sites. Flags non-standard patterns for deep scan.",
                "summary": "Parsed ERC-20 contract - 847 lines, 12 functions, 3 external call sites detected.",
            },
            {
                "id": "static",   "order": 2, "type": "subagent",  "conditional": False,
                "name": "CodeReview Pro",
                "exec_label": "Running static analysis",
                "purpose": "Sub-agent. Always called - provides code quality pass and flags structural issues before deep security scan.",
                "detail": "Checks code style, gas optimisation opportunities, and basic logic errors. Results are passed to the vulnerability scanner as annotated context.",
                "summary": "Static analysis complete - 2 gas inefficiencies, 1 logic warning passed to scanner.",
            },
            {
                "id": "scan",     "order": 3, "type": "internal",  "conditional": False,
                "name": "Vulnerability Scanner",
                "exec_label": "Scanning for vulnerabilities",
                "purpose": "Matches the annotated contract against CVE database and known DeFi exploit patterns (reentrancy, flash loan attacks, etc.).",
                "detail": "Runs 180+ security checks including reentrancy, integer overflow, access control, oracle manipulation, and front-running vectors.",
                "summary": "Scan complete - 1 critical (reentrancy in withdraw()), 1 high (missing access control).",
            },
            {
                "id": "report",   "order": 4, "type": "internal",  "conditional": False,
                "name": "Report Compiler",
                "exec_label": "Compiling audit report",
                "purpose": "Generates a prioritised audit report with issue severity, code location, exploit scenario, and recommended fix.",
                "detail": "Output includes: executive summary, per-finding breakdown with PoC exploit snippets, diff-ready patches, and a machine-readable SARIF file.",
                "summary": "Audit report compiled - 2 findings, remediation patches generated.",
            },
        ],
    },
}

# Standalone agents (no A2A) - simple 3-stage workflow
def _standalone_stages(agent_name):
    return [
        {
            "id": "parse",   "order": 1, "type": "internal", "conditional": False,
            "name": "Input Parser",
            "exec_label": "Parsing your request",
            "purpose": "Validates and normalises the input - detects task type, format, and required output structure.",
            "detail": "Handles text, files, and structured data. Extracts task intent and maps to internal processing parameters.",
            "summary": "Input parsed - task type detected, parameters extracted.",
        },
        {
            "id": "process", "order": 2, "type": "internal", "conditional": False,
            "name": "Core Processor",
            "exec_label": "Processing your request",
            "purpose": f"{agent_name}'s primary model runs the task end-to-end with no sub-agent delegation.",
            "detail": "Single-model execution. Deterministic output with no variable sub-agent costs. Completion time is fixed to the agent's average.",
            "summary": "Core processing complete.",
        },
        {
            "id": "format",  "order": 3, "type": "internal", "conditional": False,
            "name": "Output Formatter",
            "exec_label": "Formatting results",
            "purpose": "Structures the output to the requested format and runs a final quality check before delivery.",
            "detail": "Supports JSON, Markdown, PDF, and plain text output. Quality gate rejects outputs below confidence threshold.",
            "summary": "Output formatted and quality-checked - ready for delivery.",
        },
    ]

STANDALONE = {
    "composable": False,
    "stage_count": 3,
    "workflow_label": "3-stage standalone pipeline",
    "workflow_summary": "This agent operates independently. It does not call other agents.",
    "trigger_rules": [],
    "sub_agents": [],
    "base_cost_label": " - ",
    "subagent_range_label": "None",
    "total_range_label": "Base price only",
    "steps": [],
    "stages": [],
}

AGENTS = [
    {
        "id": 1,
        "name": "CodeReview Pro",
        "description": "Deep code review, security audits, and performance optimization. Supports Python, JS, Go, Rust, and 20+ languages.",
        "long_description": "CodeReview Pro is an enterprise-grade AI agent specialized in comprehensive code analysis. It performs static analysis, identifies security vulnerabilities (OWASP Top 10), suggests optimizations, and generates detailed reports. Used by 500+ engineering teams worldwide.",
        "category": "Development",
        "use_case": "Code Review",
        "verified": True,
        "verification_tier": "thorough",
        "featured": True,
        "rating": 4.8,
        "reviews": 142,
        "billing": "per_token",
        "min_price": 0.002,
        "max_price": 0.008,
        "current_price": 0.006,
        "surge_active": True,
        "surge_multiplier": 1.5,
        "seller": "DevTools Inc",
        "seller_rating": 4.9,
        "tasks_completed": 8421,
        "tags": ["code", "review", "security", "python", "javascript"],
        "capabilities": ["Static analysis", "Security audit", "Performance review", "Documentation generation", "Refactoring suggestions"],
        "avg_completion_time": "4 min",
    },
    {
        "id": 2,
        "name": "TranslateFlow",
        "description": "Real-time document and content translation across 95 languages. Preserves formatting, tone, and domain-specific terminology.",
        "long_description": "TranslateFlow uses advanced neural translation models fine-tuned for domain-specific accuracy. From legal contracts to technical manuals, it maintains context and nuance across 95 languages with 98.7% accuracy on benchmark tests.",
        "category": "Content",
        "use_case": "Translation",
        "verified": True,
        "verification_tier": "thorough",
        "featured": True,
        "rating": 4.6,
        "reviews": 89,
        "billing": "per_token",
        "min_price": 0.001,
        "max_price": 0.004,
        "current_price": 0.0015,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "LinguaAI",
        "seller_rating": 4.7,
        "tasks_completed": 12830,
        "tags": ["translation", "multilingual", "content", "NLP"],
        "capabilities": ["95 languages", "Format preservation", "Domain glossaries", "Batch processing", "Quality scoring"],
        "avg_completion_time": "2 min",
    },
    {
        "id": 3,
        "name": "DataSift Analytics",
        "description": "Autonomous data analysis agent. Feed it a CSV or database endpoint and receive structured insights, charts, and anomaly reports.",
        "long_description": "DataSift connects to your data sources and performs exploratory data analysis, statistical modeling, anomaly detection, and generates executive-level insight reports with visualizations. No SQL required.",
        "category": "Data & Analytics",
        "use_case": "Summarization",
        "verified": True,
        "verification_tier": "basic",
        "featured": False,
        "rating": 4.3,
        "reviews": 54,
        "billing": "per_minute",
        "min_price": 0.05,
        "max_price": 0.25,
        "current_price": 0.18,
        "surge_active": True,
        "surge_multiplier": 1.8,
        "seller": "Analytical Minds",
        "seller_rating": 4.4,
        "tasks_completed": 3201,
        "tags": ["analytics", "data", "CSV", "insights", "charts"],
        "capabilities": ["EDA automation", "Anomaly detection", "Report generation", "Chart creation", "Statistical modeling"],
        "avg_completion_time": "8 min",
    },
    {
        "id": 4,
        "name": "AlphaTrader AI",
        "description": "Quantitative trading signal agent. Analyzes market data and generates buy/sell signals with confidence scores.",
        "long_description": "AlphaTrader AI processes real-time and historical market data using ensemble ML models to generate trading signals. Includes risk scoring, portfolio correlation analysis, and backtesting summaries. Built for institutional-grade accuracy.",
        "category": "Finance",
        "use_case": "Trading",
        "verified": True,
        "verification_tier": "thorough",
        "featured": True,
        "rating": 4.9,
        "reviews": 201,
        "billing": "per_minute",
        "min_price": 0.10,
        "max_price": 0.50,
        "current_price": 0.45,
        "surge_active": True,
        "surge_multiplier": 2.1,
        "seller": "QuantEdge Labs",
        "seller_rating": 5.0,
        "tasks_completed": 19200,
        "tags": ["trading", "finance", "signals", "quant", "risk"],
        "capabilities": ["Signal generation", "Risk scoring", "Backtesting", "Portfolio analysis", "Real-time data"],
        "avg_completion_time": "1 min",
    },
    {
        "id": 5,
        "name": "WebCrawler X",
        "description": "Intelligent web scraping agent with anti-bot bypass, JS rendering, and structured data extraction at scale.",
        "long_description": "WebCrawler X handles complex scraping tasks including JavaScript-rendered pages, CAPTCHA bypass (ethical), pagination, and nested data extraction. Outputs clean JSON, CSV, or directly to your database.",
        "category": "Automation",
        "use_case": "Web Scraping",
        "verified": False,
        "verification_tier": "none",
        "featured": False,
        "rating": 3.9,
        "reviews": 27,
        "billing": "per_minute",
        "min_price": 0.03,
        "max_price": 0.12,
        "current_price": 0.03,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "CrawlTech",
        "seller_rating": 3.8,
        "tasks_completed": 1540,
        "tags": ["scraping", "automation", "data", "web"],
        "capabilities": ["JS rendering", "Pagination", "Structured output", "Rate limiting", "Proxy rotation"],
        "avg_completion_time": "12 min",
    },
    {
        "id": 6,
        "name": "ResearchBot Pro",
        "description": "Academic and market research agent. Queries multiple sources, synthesizes findings, and produces citation-ready summaries.",
        "long_description": "ResearchBot Pro searches across academic papers, news, reports, and databases to produce comprehensive research summaries. Supports custom citation formats (APA, MLA, Chicago) and topic-specific depth configuration.",
        "category": "Research",
        "use_case": "Summarization",
        "verified": True,
        "verification_tier": "basic",
        "featured": False,
        "rating": 4.4,
        "reviews": 73,
        "billing": "per_token",
        "min_price": 0.003,
        "max_price": 0.010,
        "current_price": 0.005,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "Cognify Research",
        "seller_rating": 4.5,
        "tasks_completed": 4890,
        "tags": ["research", "academia", "summarization", "citations"],
        "capabilities": ["Multi-source search", "Citation formatting", "Summary generation", "Topic clustering", "Fact verification"],
        "avg_completion_time": "6 min",
    },
    {
        "id": 7,
        "name": "SecureAudit AI",
        "description": "Smart contract and infrastructure security audit agent. Identifies vulnerabilities, misconfigurations, and compliance gaps.",
        "long_description": "SecureAudit AI performs comprehensive security audits of smart contracts (Solidity, Vyper), cloud infrastructure (AWS, GCP, Azure), and application codebases. Produces prioritized vulnerability reports with remediation steps.",
        "category": "Security",
        "use_case": "Code Review",
        "verified": True,
        "verification_tier": "thorough",
        "featured": False,
        "rating": 4.7,
        "reviews": 96,
        "billing": "per_token",
        "min_price": 0.005,
        "max_price": 0.020,
        "current_price": 0.015,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "AuditShield",
        "seller_rating": 4.8,
        "tasks_completed": 2340,
        "tags": ["security", "audit", "smart contracts", "vulnerability"],
        "capabilities": ["Smart contract audit", "Cloud security", "Compliance check", "Penetration testing", "Remediation guide"],
        "avg_completion_time": "15 min",
    },
    {
        "id": 8,
        "name": "ContentForge",
        "description": "Long-form content generation agent for blogs, whitepapers, and marketing copy. Brand-voice configurable.",
        "long_description": "ContentForge generates high-quality long-form content with SEO optimization, brand voice alignment, and multimedia asset suggestions. Supports 40+ content types from blog posts to technical whitepapers.",
        "category": "Content",
        "use_case": "Translation",
        "verified": False,
        "verification_tier": "none",
        "featured": False,
        "rating": 3.7,
        "reviews": 18,
        "billing": "per_token",
        "min_price": 0.001,
        "max_price": 0.005,
        "current_price": 0.001,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "CreateAI",
        "seller_rating": 3.6,
        "tasks_completed": 890,
        "tags": ["content", "writing", "SEO", "marketing", "blog"],
        "capabilities": ["Long-form writing", "SEO optimization", "Brand voice", "Multi-format", "Plagiarism check"],
        "avg_completion_time": "5 min",
    },
    {
        "id": 9,
        "name": "ImageGen Studio",
        "description": "Commercial-grade image generation agent. Produces photorealistic and artistic images from text prompts at scale.",
        "long_description": "ImageGen Studio generates high-resolution images (up to 4K) using state-of-the-art diffusion models. Supports style presets, negative prompts, batch generation, and commercial licensing on all outputs.",
        "category": "Content",
        "use_case": "Image Generation",
        "verified": True,
        "verification_tier": "basic",
        "featured": False,
        "rating": 4.5,
        "reviews": 188,
        "billing": "per_token",
        "min_price": 0.002,
        "max_price": 0.012,
        "current_price": 0.008,
        "surge_active": True,
        "surge_multiplier": 1.3,
        "seller": "PixelMind AI",
        "seller_rating": 4.6,
        "tasks_completed": 32100,
        "tags": ["images", "generation", "diffusion", "creative", "commercial"],
        "capabilities": ["4K resolution", "Style presets", "Batch generation", "Commercial license", "Negative prompts"],
        "avg_completion_time": "45 sec",
    },
    {
        "id": 10,
        "name": "TestingMaster",
        "description": "Automated test generation agent. Writes unit tests, integration tests, and end-to-end test suites from source code.",
        "long_description": "TestingMaster analyzes your codebase and generates comprehensive test suites including unit tests, integration tests, and E2E tests. Achieves 90%+ coverage targets automatically with meaningful test cases.",
        "category": "Development",
        "use_case": "Testing",
        "verified": True,
        "verification_tier": "basic",
        "featured": False,
        "rating": 4.2,
        "reviews": 61,
        "billing": "per_token",
        "min_price": 0.002,
        "max_price": 0.009,
        "current_price": 0.004,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "QualityFirst",
        "seller_rating": 4.3,
        "tasks_completed": 5670,
        "tags": ["testing", "QA", "unit tests", "automation", "coverage"],
        "capabilities": ["Unit test generation", "Integration tests", "E2E tests", "Coverage analysis", "CI/CD integration"],
        "avg_completion_time": "7 min",
    },
    {
        "id": 11,
        "name": "FinanceGPT",
        "description": "Financial modeling and forecasting agent. Builds DCF models, scenario analysis, and investor-ready reports.",
        "long_description": "FinanceGPT automates financial modeling workflows including DCF valuation, Monte Carlo simulations, sensitivity analysis, and report generation. Connects to live market data APIs for real-time inputs.",
        "category": "Finance",
        "use_case": "Summarization",
        "verified": True,
        "verification_tier": "thorough",
        "featured": False,
        "rating": 4.6,
        "reviews": 44,
        "billing": "per_minute",
        "min_price": 0.08,
        "max_price": 0.30,
        "current_price": 0.20,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "QuantEdge Labs",
        "seller_rating": 5.0,
        "tasks_completed": 1820,
        "tags": ["finance", "modeling", "DCF", "forecasting", "valuation"],
        "capabilities": ["DCF modeling", "Monte Carlo", "Scenario analysis", "Report generation", "Live market data"],
        "avg_completion_time": "10 min",
    },
    {
        "id": 13,
        "name": "ResumeBot AI",
        "description": "AI-powered resume reviewer and career coach. Rewrites bullet points, scores ATS compatibility, and tailors your resume to any job description.",
        "long_description": "ResumeBot AI analyzes your resume against job descriptions using NLP and ATS compatibility scoring. It rewrites weak bullet points using the STAR framework, suggests skills to add, flags formatting issues, and generates a tailored cover letter. Used by 10,000+ job seekers with an 87% interview rate improvement.",
        "category": "Content",
        "use_case": "Resume & Career",
        "verified": True,
        "verification_tier": "thorough",
        "featured": True,
        "rating": 4.7,
        "reviews": 312,
        "billing": "per_token",
        "min_price": 0.001,
        "max_price": 0.006,
        "current_price": 0.003,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "CareerAI Labs",
        "seller_rating": 4.8,
        "tasks_completed": 10420,
        "tags": ["resume", "career", "job search", "ATS", "cover letter", "interview"],
        "capabilities": ["ATS scoring", "Bullet point rewriting", "Job description matching", "Cover letter generation", "Skills gap analysis"],
        "avg_completion_time": "3 min",
    },
    {
        "id": 12,
        "name": "AutoDoc AI",
        "description": "Automatic documentation agent. Generates API docs, inline comments, and README files from any codebase.",
        "long_description": "AutoDoc AI reads your entire codebase and produces comprehensive documentation including API references, inline JSDoc/docstrings, README files, and architecture diagrams. Supports 15+ frameworks.",
        "category": "Development",
        "use_case": "Code Review",
        "verified": False,
        "verification_tier": "none",
        "featured": False,
        "rating": 4.0,
        "reviews": 32,
        "billing": "per_token",
        "min_price": 0.001,
        "max_price": 0.006,
        "current_price": 0.002,
        "surge_active": False,
        "surge_multiplier": 1.0,
        "seller": "DocMaster",
        "seller_rating": 4.1,
        "tasks_completed": 2100,
        "tags": ["documentation", "API", "README", "developer tools"],
        "capabilities": ["API docs", "Inline comments", "README generation", "Architecture diagrams", "Multi-framework"],
        "avg_completion_time": "5 min",
    },
]

ORDERS = [
    {"id": "ORD-001", "agent": "CodeReview Pro", "agent_id": 1, "buyer": "0x1a2b...3c4d", "amount": 12.40, "status": "completed", "date": "2026-04-14", "task": "Review authentication module"},
    {"id": "ORD-002", "agent": "AlphaTrader AI", "agent_id": 4, "buyer": "0x5e6f...7g8h", "amount": 27.00, "status": "in_progress", "date": "2026-04-15", "task": "Generate signals for BTC/ETH"},
    {"id": "ORD-003", "agent": "TranslateFlow", "agent_id": 2, "buyer": "0x9i0j...1k2l", "amount": 3.20, "status": "completed", "date": "2026-04-13", "task": "Translate privacy policy to 5 languages"},
    {"id": "ORD-004", "agent": "SecureAudit AI", "agent_id": 7, "buyer": "0x3m4n...5o6p", "amount": 45.00, "status": "in_escrow", "date": "2026-04-15", "task": "Audit ERC-20 token contract"},
    {"id": "ORD-005", "agent": "DataSift Analytics", "agent_id": 3, "buyer": "0x7q8r...9s0t", "amount": 18.00, "status": "completed", "date": "2026-04-12", "task": "Analyze Q1 sales data"},
]

VERIFICATION_QUEUE = [
    {"id": "VRF-001", "agent": "ContentForge", "agent_id": 8, "seller": "CreateAI", "tier": "basic", "status": "testing", "submitted": "2026-04-14", "safety_score": 91, "performance_score": 78, "reliability_score": 85},
    {"id": "VRF-002", "agent": "WebCrawler X", "agent_id": 5, "seller": "CrawlTech", "tier": "basic", "status": "human_review", "submitted": "2026-04-13", "safety_score": 88, "performance_score": 82, "reliability_score": 79},
    {"id": "VRF-003", "agent": "AutoDoc AI", "agent_id": 12, "seller": "DocMaster", "tier": "basic", "status": "pending", "submitted": "2026-04-15", "safety_score": None, "performance_score": None, "reliability_score": None},
    {"id": "VRF-004", "agent": "MLOps Agent", "agent_id": None, "seller": "PipelineAI", "tier": "thorough", "status": "pending", "submitted": "2026-04-15", "safety_score": None, "performance_score": None, "reliability_score": None},
    {"id": "VRF-005", "agent": "NLP Extractor", "agent_id": None, "seller": "TextLabs", "tier": "thorough", "status": "testing", "submitted": "2026-04-14", "safety_score": 95, "performance_score": 91, "reliability_score": 94},
]

PAYOUTS_SEED = [
    {"id": "PAY-001", "seller": "DevTools Inc",   "agent": "CodeReview Pro",    "amount": 1240.50, "status": "pending",  "date": "2026-04-15", "order_id": "ORD-001"},
    {"id": "PAY-002", "seller": "QuantEdge Labs", "agent": "AlphaTrader AI",    "amount": 3820.00, "status": "pending",  "date": "2026-04-15", "order_id": "ORD-002"},
    {"id": "PAY-003", "seller": "LinguaAI",       "agent": "TranslateFlow",     "amount": 540.20,  "status": "released", "date": "2026-04-14", "order_id": "ORD-003"},
    {"id": "PAY-004", "seller": "AuditShield",    "agent": "SecureAudit AI",    "amount": 2100.00, "status": "released", "date": "2026-04-14", "order_id": "ORD-004"},
    {"id": "PAY-005", "seller": "CrawlTech",      "agent": "WebCrawler X",      "amount": 180.00,  "status": "held",     "date": "2026-04-13", "order_id": None},
]

MODERATION_SEED = [
    {"id": "RPT-001", "agent": "WebCrawler X",  "agent_id": 5, "reporter": "0x1a2b...3c", "reason": "Excessive scraping caused rate limit violations on third-party APIs.",     "status": "open",          "date": "2026-04-14"},
    {"id": "RPT-002", "agent": "ContentForge",  "agent_id": 8, "reporter": "0x4d5e...6f", "reason": "Output quality fell below the advertised level on two consecutive tasks.", "status": "investigating", "date": "2026-04-13"},
    {"id": "RPT-003", "agent": "AutoDoc AI",    "agent_id": 12, "reporter": "0x7a8b...9c", "reason": "Generated documentation contained inaccurate API signatures.",             "status": "resolved",      "date": "2026-04-12"},
]

REVIEWS_SEED = [
    {"agent_id": 1, "user": "0x3a4b...5c", "rating": 5, "comment": "Fast and accurate. Saved our team hours of manual review.", "date": "2026-04-12"},
    {"agent_id": 1, "user": "0x7f8e...2a", "rating": 4, "comment": "Strong results overall. Surge pricing was steep during peak hours.", "date": "2026-04-10"},
    {"agent_id": 1, "user": "0x1d2e...9f", "rating": 5, "comment": "Best code review agent on the marketplace for this use case.", "date": "2026-04-08"},
    {"agent_id": 2, "user": "0x2b3c...4d", "rating": 5, "comment": "Translated 5 languages cleanly with correct legal phrasing.", "date": "2026-04-13"},
    {"agent_id": 3, "user": "0x5e6f...7a", "rating": 4, "comment": "Pulled clean CSV outputs with reasonable column typing.", "date": "2026-04-11"},
    {"agent_id": 4, "user": "0x8b9c...0d", "rating": 5, "comment": "Signal set identified a clear macro setup. Great confidence scores.", "date": "2026-04-09"},
    {"agent_id": 7, "user": "0xa1b2...c3", "rating": 5, "comment": "Found two high-severity issues our existing static tools missed.", "date": "2026-04-07"},
    {"agent_id": 13, "user": "0xd4e5...f6", "rating": 5, "comment": "ATS score jumped from 62 to 91 after the rewrite. Landed an interview the same week.", "date": "2026-04-06"},
]

EARNINGS_DATA = {
    "total_revenue": 8420.50,
    "platform_fees": 84.21,
    "escrow_funds": 312.00,
    "released_payouts": 8024.29,
    "monthly": [2100, 2840, 3200, 4100, 3800, 4500, 5200, 4900, 6100, 7200, 7800, 8420],
    "surge_earnings": [210, 340, 480, 620, 510, 680, 890, 720, 980, 1240, 1380, 1620],
    "labels": ["May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr"],
}

ADMIN_STATS = {
    "total_agents": len(AGENTS),
    "verified_agents": len([a for a in AGENTS if a["verified"]]),
    "pending_verifications": len([v for v in VERIFICATION_QUEUE if v["status"] in ("pending", "testing", "human_review")]),
    "active_orders": len([o for o in ORDERS if o["status"] == "in_progress"]),
    "total_volume": 142830.00,
    "surge_revenue_pct": 18.4,
    "hourly_revenue": [120, 85, 60, 45, 90, 180, 320, 410, 390, 450, 480, 520, 490, 510, 530, 480, 460, 510, 580, 620, 540, 480, 380, 250],
    "revenue_labels": [f"{i:02d}:00" for i in range(24)],
}

# ── Routes ─────────────────────────────────────────────────────────────────────

_CAT_CODES = {
    "Development": "DEV", "Data & Analytics": "DAT", "Content": "CON",
    "Finance": "FIN", "Research": "RES", "Security": "SEC", "Automation": "AUT",
}

@app.route("/")
def index():
    """Standalone landing page. First thing visitors see. Click-through to /marketplace."""
    featured = [a for a in AGENTS if a["featured"]]

    # Build the interactive network-visualization dataset.
    # Nodes: first 12 agents (keeps the canvas readable). Edges: derived
    # from real A2A workflow sub-agent relationships, so the viz reflects
    # actual on-chain agent composition, not decoration.
    _agent_ids = {a["id"] for a in AGENTS[:12]}
    viz_agents = [
        {
            "id":         a["id"],
            "name":       a["name"],
            "cat":        _CAT_CODES.get(a["category"], "AGT"),
            "verified":   a["verified"],
            "featured":   a["featured"],
            "price":      a["current_price"],
            "unit":       "tok" if a["billing"] == "per_token" else "min",
            "surge":      a.get("surge_active", False),
            "surge_mult": a.get("surge_multiplier", 1.0),
            "rating":     a.get("rating", 4.0),
            "tasks":      a.get("tasks_completed", 0),
        }
        for a in AGENTS[:12]
    ]
    viz_edges = []
    _seen = set()
    for parent_id, wf in A2A_WORKFLOWS.items():
        if parent_id not in _agent_ids:
            continue
        for sub in wf.get("sub_agents", []):
            sub_id = sub.get("id")
            if sub_id in _agent_ids and (parent_id, sub_id) not in _seen and (sub_id, parent_id) not in _seen:
                viz_edges.append({"source": parent_id, "target": sub_id})
                _seen.add((parent_id, sub_id))

    return render_template(
        "landing.html",
        featured=featured,
        viz_agents=viz_agents,
        viz_edges=viz_edges,
        stats={
            "total_agents": len(AGENTS),
            "tasks_completed": sum(a["tasks_completed"] for a in AGENTS),
            "usdc_settled": 142830,
            "verified_agents": len([a for a in AGENTS if a["verified"]]),
        },
    )

@app.route("/marketplace")
def marketplace():
    category  = request.args.get("category", "")
    use_case  = request.args.get("use_case", "")
    verified  = request.args.get("verified", "")
    featured  = request.args.get("featured", "")
    sort      = request.args.get("sort", "relevance")
    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")
    query     = request.args.get("q", "")

    agents = AGENTS[:]

    if query:
        q = query.lower()
        agents = [a for a in agents if q in a["name"].lower() or q in a["description"].lower() or any(q in t for t in a["tags"])]
    if category:
        agents = [a for a in agents if a["category"] == category]
    if use_case:
        agents = [a for a in agents if a["use_case"] == use_case]
    if verified == "verified":
        agents = [a for a in agents if a["verified"]]
    elif verified == "unverified":
        agents = [a for a in agents if not a["verified"]]
    if featured:
        agents = [a for a in agents if a["featured"]]

    if sort == "price_low":
        agents.sort(key=lambda a: a["current_price"])
    elif sort == "price_high":
        agents.sort(key=lambda a: a["current_price"], reverse=True)
    elif sort == "rating":
        agents.sort(key=lambda a: a["rating"], reverse=True)
    elif sort == "newest":
        agents = list(reversed(agents))

    return render_template("marketplace.html", agents=agents, categories=CATEGORIES,
                           use_cases=USE_CASES, filters={"category": category, "use_case": use_case,
                           "verified": verified, "sort": sort, "q": query, "featured": featured})

@app.route("/agent/<int:agent_id>")
def agent_detail(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return redirect(url_for("marketplace"))
    # Load real reviews from DB (buyer ratings persist across sessions).
    try:
        from models import Review as ReviewModel
        rows = (ReviewModel.query
                .filter_by(agent_id=agent_id)
                .order_by(ReviewModel.created_at.desc())
                .limit(10).all())
        reviews = [r.to_dict() for r in rows]
    except Exception:
        reviews = []
    a2a = A2A_WORKFLOWS.get(agent_id, {**STANDALONE, "stages": _standalone_stages(agent["name"])})
    return render_template("agent_detail.html", agent=agent, reviews=reviews, a2a=a2a)

@app.route("/checkout/<int:agent_id>", methods=["GET", "POST"])
def checkout(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return redirect(url_for("marketplace"))
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        order_id = f"ORD-{len(ORDERS) + 1:03d}"
        new_order = {
            "id": order_id,
            "agent": agent["name"],
            "agent_id": agent_id,
            "buyer": data.get("buyer", "0x0000...0000"),
            "amount": float(data.get("amount", 0)),
            "status": "in_escrow",
            "date": str(uuid.uuid4())[:10],
            "task": data.get("task", ""),
        }
        ORDERS.append(new_order)
        if request.is_json:
            return jsonify({"orderId": order_id, "status": "in_escrow"}), 201
        return redirect(url_for("order_detail", order_id=order_id))
    a2a = A2A_WORKFLOWS.get(agent_id, {**STANDALONE, "stages": _standalone_stages(agent["name"])})
    return render_template("checkout.html", agent=agent, a2a=a2a)

@app.route("/order/<order_id>")
def order_detail(order_id):
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if not order:
        # Fall back to DB (x402 payments create Order rows keyed by session id).
        try:
            from models import Order as OrderModel
            db_order = OrderModel.query.get(order_id)
            if db_order:
                order = db_order.to_dict()
        except Exception:
            order = None
    if not order:
        return render_template("404.html", missing=f"order {order_id}"), 404
    agent = next((a for a in AGENTS if a["id"] == order["agent_id"]), None)
    if not agent:
        return render_template("404.html", missing=f"agent for order {order_id}"), 404
    a2a   = A2A_WORKFLOWS.get(agent["id"], {**STANDALONE, "stages": _standalone_stages(agent["name"])})
    return render_template("order.html", order=order, agent=agent, a2a=a2a)

@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")

@app.route("/list-your-agent")
def list_your_agent():
    return redirect(url_for("seller_create"))

# ── Seller ─────────────────────────────────────────────────────────────────────

@app.route("/seller/dashboard")
def seller_dashboard():
    seller = request.args.get("seller", "").strip()
    if seller:
        my_agents = [a for a in AGENTS if a["seller"].lower() == seller.lower()]
        my_order_names = {a["name"] for a in my_agents}
        my_orders = [o for o in ORDERS if o["agent"] in my_order_names]
    else:
        # Demo default: first seller's agents, with any orders for those agents.
        default_seller = AGENTS[0]["seller"] if AGENTS else ""
        my_agents = [a for a in AGENTS if a["seller"] == default_seller]
        my_order_names = {a["name"] for a in my_agents}
        my_orders = [o for o in ORDERS if o["agent"] in my_order_names]
        seller = default_seller
    return render_template("seller/dashboard.html",
                           agents=my_agents, orders=my_orders,
                           earnings=EARNINGS_DATA, seller=seller)

@app.route("/seller/create", methods=["GET", "POST"])
def seller_create():
    if request.method == "POST":
        from models import Agent as AgentModel, OnchainProfile, VerificationEntry
        import re
        data = request.get_json(silent=True) or request.form.to_dict()

        # Required fields — wallet + stake now mandatory
        required = ["name", "description", "category", "billing", "wallet", "stake_tier"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            return jsonify({"error": f"missing required fields: {missing}"}), 400

        wallet = str(data["wallet"]).strip()
        if not re.fullmatch(r"0x[a-fA-F0-9]{40}", wallet):
            return jsonify({"error": "wallet must be a valid 0x-prefixed 40-hex address"}), 400

        stake_tier = int(data.get("stake_tier") or 1)
        stake_tier = max(1, min(3, stake_tier))
        stake_amount_usdc = {1: 100, 2: 500, 3: 2000}[stake_tier]
        stake_micro = stake_amount_usdc * 1_000_000

        # Persist the agent row
        row = AgentModel(
            name=data["name"],
            description=data.get("description", ""),
            long_description=data.get("long_description", data.get("description", "")),
            category=data["category"],
            use_case=data.get("use_case", ""),
            verified=False, verification_tier="none", featured=False,
            rating=0.0, reviews=0,
            billing=data["billing"],
            min_price=float(data.get("min_price", 0.001)),
            max_price=float(data.get("max_price", 0.010)),
            current_price=float(data.get("min_price", 0.001)),
            surge_active=False, surge_multiplier=1.0,
            seller=data.get("seller") or "Unknown Seller",
            seller_rating=0.0, tasks_completed=0,
            avg_completion_time=data.get("avg_completion_time", " - "),
        )
        row.tags = [t.strip() for t in (data.get("tags") or "").split(",") if t.strip()]
        row.capabilities = [c.strip() for c in (data.get("capabilities") or "").split("\n") if c.strip()]
        db.session.add(row)
        db.session.flush()   # populate row.id

        # Staking gate: create the OnchainProfile with the chosen stake.
        # Listings only go live when a profile exists — no stake, no listing.
        profile = OnchainProfile(
            agent_id=row.id,
            wallet_address=wallet.lower(),
            score=500, tier=stake_tier, tasks_completed=0,
            staked_amount=stake_micro, accepting_work=True,
        )
        db.session.add(profile)

        # Verification queue entry (unchanged behavior)
        db.session.add(VerificationEntry(
            id=f"VRF-{row.id:03d}",
            agent_id=row.id, agent_name=row.name, seller=row.seller,
            tier=data.get("verification_tier", "basic"),
            status="pending", submitted=str(uuid.uuid4())[:10],
        ))

        # Also push into the in-memory AGENTS list so other code paths that
        # still iterate over AGENTS keep seeing the new row.
        AGENTS.append({
            "id": row.id, "name": row.name, "description": row.description,
            "long_description": row.long_description, "category": row.category,
            "use_case": row.use_case, "verified": False, "verification_tier": "none",
            "featured": False, "rating": 0.0, "reviews": 0, "billing": row.billing,
            "min_price": row.min_price, "max_price": row.max_price,
            "current_price": row.current_price, "surge_active": False,
            "surge_multiplier": 1.0, "seller": row.seller, "seller_rating": 0.0,
            "tasks_completed": 0, "tags": row.tags, "capabilities": row.capabilities,
            "avg_completion_time": row.avg_completion_time,
            "stake_tier": stake_tier, "stake_usdc": stake_amount_usdc,
            "wallet": wallet,
        })

        db.session.commit()
        log.info("New agent %s (id=%d) listed by %s  wallet=%s  stake=T%d/%d USDC",
                 row.name, row.id, row.seller, wallet, stake_tier, stake_amount_usdc)

        # Best-effort on-chain registration. Runs only when the facilitator key
        # is configured AND funded; silent fallback to DB-only otherwise.
        chain_info = {"onChain": False}
        oc = _get_onchain()
        if oc:
            try:
                endpoint = f"https://agents.agenthire.io/{row.id}"
                result = oc.register_agent(wallet, row.name, endpoint)
                chain_info = {
                    "onChain": True,
                    "chainAgentId": result.get("agentId"),
                    "txHash": result.get("txHash"),
                    "snowtrace": result.get("snowtrace"),
                }
                log.info("On-chain register ok  chainAgentId=%s tx=%s",
                         result.get("agentId"), result.get("txHash"))
            except Exception as chain_err:
                log.warning("On-chain register failed (DB listing still live): %s", chain_err)

        if request.is_json:
            return jsonify({
                "agentId": row.id, "status": "listed",
                "wallet": wallet, "stakeTier": stake_tier,
                "stakeUSDC": stake_amount_usdc,
                "message": "Agent listed. Stake escrowed to StakingSlashing.",
                **chain_info,
            }), 201
        return redirect(url_for("agent_detail", agent_id=row.id))
    return render_template("seller/create.html", categories=CATEGORIES, use_cases=USE_CASES)

@app.route("/seller/verification")
def seller_verification():
    my_queue = VERIFICATION_QUEUE[:3]
    return render_template("seller/verification.html", queue=my_queue)

@app.route("/seller/orders")
def seller_orders():
    seller = request.args.get("seller", "").strip()
    if seller:
        names = {a["name"] for a in AGENTS if a["seller"].lower() == seller.lower()}
    else:
        default_seller = AGENTS[0]["seller"] if AGENTS else ""
        names = {a["name"] for a in AGENTS if a["seller"] == default_seller}
        seller = default_seller
    orders = [o for o in ORDERS if o["agent"] in names]
    return render_template("seller/orders.html", orders=orders, seller=seller)

@app.route("/seller/earnings")
def seller_earnings():
    return render_template("seller/earnings.html", earnings=EARNINGS_DATA)


@app.route("/seller/agents/<int:agent_id>", methods=["GET", "POST"])
def seller_manage_agent(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return redirect(url_for("seller_dashboard"))
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        action = data.get("action", "")
        if action == "pause":
            agent["surge_active"] = False
            agent["verification_tier"] = agent.get("verification_tier", "none") + "_paused" if not agent.get("verification_tier", "").endswith("_paused") else agent["verification_tier"]
            log.info("Agent %s paused by seller", agent_id)
            return jsonify({"agentId": agent_id, "status": "paused"})
        elif action == "reactivate":
            log.info("Agent %s reactivated by seller", agent_id)
            return jsonify({"agentId": agent_id, "status": "active"})
        elif action == "update":
            for field in ["name", "description", "min_price", "max_price", "tags"]:
                if field in data:
                    if field in ("min_price", "max_price"):
                        agent[field] = float(data[field])
                    elif field == "tags":
                        agent[field] = [t.strip() for t in data[field].split(",") if t.strip()]
                    else:
                        agent[field] = data[field]
            log.info("Agent %s updated by seller", agent_id)
            return jsonify({"agentId": agent_id, "status": "updated"})
    return render_template("seller/manage.html", agent=agent, categories=CATEGORIES)

# ── Admin ──────────────────────────────────────────────────────────────────────

@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin/dashboard.html", stats=ADMIN_STATS, agents=AGENTS)

@app.route("/admin/verification-queue")
def admin_verification_queue():
    return render_template("admin/verification_queue.html", queue=VERIFICATION_QUEUE)


@app.route("/admin/sandbox")
def admin_sandbox():
    """Sandbox / security gate testing results for agent submissions."""
    # Each entry corresponds to a verification queue item that has been tested
    sandbox_results = [
        {
            "vrf_id": "VRF-001", "agent": "ContentForge", "seller": "CreateAI", "tier": "basic",
            "submitted": "2026-04-14", "completed": "2026-04-14",
            "gates": {
                "static_scan":    {"status": "pass", "score": 91, "notes": "No hidden instructions. 3 low-severity dependency warnings."},
                "sandbox":        {"status": "pass", "score": 85, "notes": "Ran 200 prompts. No canary token leaks. Max execution: 12s."},
                "gatekeeper_ai":  {"status": "pass", "score": 88, "notes": "Adversarial session: no jailbreaks. Policy compliance confirmed."},
                "model_fingerprint": {"status": "pass", "score": 100, "notes": "Model identity verified. Not a resubmission."},
            },
            "overall": "pass", "verdict": "Safe to list at Basic tier.",
        },
        {
            "vrf_id": "VRF-002", "agent": "WebCrawler X", "seller": "CrawlTech", "tier": "basic",
            "submitted": "2026-04-13", "completed": "2026-04-13",
            "gates": {
                "static_scan":    {"status": "pass",    "score": 88, "notes": "Permissions audit clean. No hidden network calls."},
                "sandbox":        {"status": "warning", "score": 72, "notes": "Rate limit violations detected under load. Flagged for human review."},
                "gatekeeper_ai":  {"status": "pass",    "score": 82, "notes": "No adversarial escapes."},
                "model_fingerprint": {"status": "pass", "score": 100, "notes": "Unique model identity confirmed."},
            },
            "overall": "warning", "verdict": "Sandbox concerns - escalated to human review.",
        },
        {
            "vrf_id": "VRF-005", "agent": "NLP Extractor", "seller": "TextLabs", "tier": "thorough",
            "submitted": "2026-04-14", "completed": "2026-04-14",
            "gates": {
                "static_scan":    {"status": "pass", "score": 95, "notes": "All clear. Minimal dependency surface."},
                "sandbox":        {"status": "pass", "score": 91, "notes": "500 prompts. Sub-100ms response. No leaks."},
                "gatekeeper_ai":  {"status": "pass", "score": 94, "notes": "Two adversarial models used. Zero policy violations."},
                "model_fingerprint": {"status": "pass", "score": 100, "notes": "Novel model. First submission."},
            },
            "overall": "pass", "verdict": "Excellent scores. Recommended for Thorough Audit badge.",
        },
    ]
    return render_template("admin/sandbox.html", results=sandbox_results)


@app.route("/admin/review/<vrf_id>", methods=["GET", "POST"])
def admin_human_review(vrf_id):
    """Human review panel for Thorough Audit tier agents."""
    entry = next((v for v in VERIFICATION_QUEUE if v["id"] == vrf_id), None)
    if not entry:
        return redirect(url_for("admin_verification_queue"))
    agent = next((a for a in AGENTS if a["id"] == entry.get("agent_id")), None)
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        action = data.get("action")
        if action == "approve":
            entry["status"] = "approved"
            if agent:
                agent["verified"] = True
                agent["verification_tier"] = entry.get("tier", "basic")
            log.info("Human review approved: %s", vrf_id)
            return jsonify({"id": vrf_id, "status": "approved"})
        elif action == "reject":
            entry["status"] = "rejected"
            log.info("Human review rejected: %s notes=%s", vrf_id, data.get("notes", ""))
            return jsonify({"id": vrf_id, "status": "rejected"})
    return render_template("admin/review.html", entry=entry, agent=agent)

@app.route("/admin/moderation")
def admin_moderation():
    from models import ModerationReport
    reports = [r.to_dict() for r in
               ModerationReport.query.order_by(ModerationReport.created_at.desc()).all()]
    return render_template("admin/moderation.html", reports=reports)


@app.route("/admin/payouts")
def admin_payouts():
    from models import Payout
    payouts = [p.to_dict() for p in
               Payout.query.order_by(Payout.created_at.desc()).all()]
    return render_template("admin/payouts.html", payouts=payouts, stats=ADMIN_STATS)

# ── API (mock) ─────────────────────────────────────────────────────────────────

@app.route("/api/price/<int:agent_id>")
@limiter.limit("60/minute")
def api_price(agent_id):
    from models import Agent as AgentModel, PricePoint
    from simulation import current_price
    agent_row = AgentModel.query.get(agent_id)
    if not agent_row:
        return jsonify({"error": "not found"}), 404
    # Pull the most-recent simulation point for utilization / demand signal.
    latest = (
        PricePoint.query
        .filter_by(agent_id=agent_id)
        .order_by(PricePoint.ts.desc())
        .first()
    )
    util = latest.utilization if latest else 0.4
    demand = min(1.0, util + random.uniform(-0.05, 0.1))
    quote = current_price(agent_row, utilization=util, demand=demand)
    return jsonify({
        "price": quote["currentPrice"],
        "surge": quote["surgeActive"],
        "multiplier": quote["surgeMultiplier"],
        "minPrice": quote["minPrice"],
        "maxPrice": quote["maxPrice"],
        "utilization": quote["utilization"],
        "demand": quote["demand"],
    })

# ── x402 / on-chain integration ────────────────────────────────────────────────
# Three layers of degradation:
#   (1) FACILITATOR_URL env set → proxy to Node facilitator (fastest for dev)
#   (2) FACILITATOR_PRIVATE_KEY set → use onchain.py (Python-native, no Node)
#   (3) neither → mock responses (demo UI without any backend)
import os
import uuid
FACILITATOR_URL = os.environ.get("FACILITATOR_URL")

_onchain = None
def _get_onchain():
    global _onchain
    if _onchain is None:
        try:
            from onchain import OnChain
            _onchain = OnChain.from_env()
        except Exception as e:
            print(f"[onchain] unavailable: {e}")
            _onchain = False
    return _onchain or None

def _record_order_from_payment(session_id: str, agent_id: int, buyer: str, amount_usdc: float) -> None:
    """Persist a new Order row so /order/<sessionId> renders the real agent + amount."""
    from models import Order as OrderModel
    try:
        sid = str(session_id)
        if not sid:
            return
        agent = next((a for a in AGENTS if a["id"] == int(agent_id)), None)
        agent_name = agent["name"] if agent else f"Agent #{agent_id}"
        today = time.strftime("%Y-%m-%d")
        # In-memory mirror
        ORDERS.append({
            "id": sid, "agent": agent_name, "agent_id": int(agent_id),
            "buyer": buyer or "0x0000...0000", "amount": float(amount_usdc),
            "status": "in_escrow", "date": today,
            "task": "Escrow session opened via x402",
        })
        # DB row (if schema allows)
        if not OrderModel.query.get(sid):
            db.session.add(OrderModel(
                id=sid, agent_id=int(agent_id), buyer=(buyer or "0x0000...0000"),
                amount=float(amount_usdc), status="in_escrow",
                task="Escrow session opened via x402", date=today,
            ))
            db.session.commit()
    except Exception as e:
        log.warning("Failed to record Order %s: %s", session_id, e)


@app.route("/api/x402/pay", methods=["POST"])
@limiter.limit("30/minute")
def api_x402_pay():
    payload = request.get_json(silent=True) or {}
    required = ["from", "to", "value", "validBefore", "nonce", "v", "r", "s", "agentId"]
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    # Amount is in USDC micro-units in the permit; convert to human USDC for display.
    try:
        amount_usdc = float(int(payload["value"])) / 1_000_000.0
    except Exception:
        amount_usdc = 0.0
    buyer_addr = payload.get("from", "")
    agent_id = payload.get("agentId")

    if FACILITATOR_URL:
        try:
            import requests
            r = requests.post(f"{FACILITATOR_URL}/x402/execute", json=payload, timeout=30)
            if r.ok:
                try:
                    body = r.json()
                    if body.get("sessionId"):
                        _record_order_from_payment(body["sessionId"], agent_id, buyer_addr, amount_usdc)
                except Exception:
                    pass
            return (r.text, r.status_code, r.headers.items())
        except Exception as e:
            return jsonify({"error": f"facilitator unreachable: {e}"}), 502

    oc = _get_onchain()
    if oc and oc.facilitator:
        try:
            result = oc.x402_execute(payload)
            if result.get("sessionId"):
                _record_order_from_payment(result["sessionId"], agent_id, buyer_addr, amount_usdc)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": f"onchain x402 failed: {e}"}), 500

    # Mockup fallback: pretend the payment went through, but still record an Order
    # so the buyer can navigate to /order/<sessionId> and see real data.
    session_id = str(uuid.uuid4())[:8]
    _record_order_from_payment(session_id, agent_id, buyer_addr, amount_usdc)
    return jsonify({
        "sessionId": session_id,
        "agentId": agent_id,
        "status": "mock_settled",
        "note": "No FACILITATOR_URL and no FACILITATOR_PRIVATE_KEY. Mock response. Set either to enable real on-chain.",
    })

# Submit a dispute. Proxies to the gatekeeper backend, which (optionally) signs
# an on-chain incident. If GATEKEEPER_URL not set, logs + returns pending.
@app.route("/api/dispute/submit", methods=["POST"])
def api_dispute_submit():
    payload = request.get_json(silent=True) or {}
    required = ["agentId", "severity", "reason", "affectedUser"]
    for k in required:
        if k not in payload:
            return jsonify({"error": f"missing {k}"}), 400

    gk_url = os.environ.get("GATEKEEPER_URL")
    if gk_url:
        try:
            import requests
            r = requests.post(f"{gk_url}/incident/sign", json=payload, timeout=15)
            return (r.text, r.status_code, r.headers.items())
        except Exception as e:
            return jsonify({"error": f"gatekeeper unreachable: {e}"}), 502

    oc = _get_onchain()
    if oc and oc.gatekeeper:
        try:
            return jsonify(oc.submit_incident(
                int(payload["agentId"]),
                payload["affectedUser"],
                int(payload["severity"]),
            ))
        except Exception as e:
            return jsonify({"error": f"onchain gatekeeper failed: {e}"}), 500

    # Mock path: log and accept without signing
    print(f"[dispute] agent={payload['agentId']} sev={payload['severity']} reason={payload['reason']!r}")
    return jsonify({
        "status": "pending_review",
        "note": "No GATEKEEPER_URL and no GATEKEEPER_PRIVATE_KEY - dispute logged but no on-chain incident was signed.",
    })


# Read a live escrow session from chain. Prefers Python-native onchain.py,
# falls back to the Node facilitator if configured.
@app.route("/api/session/<session_id>")
def api_session(session_id):
    try:
        sid = int(session_id)
    except ValueError:
        return jsonify({"error": "session id must be numeric"}), 400
    oc = _get_onchain()
    if oc:
        try:
            s = oc.get_session(sid)
            # Contract returns zero-struct for unknown sessions; map that to 404.
            if s.get("user") == "0x0000000000000000000000000000000000000000":
                return jsonify({"error": "session not found"}), 404
            return jsonify(s)
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    if FACILITATOR_URL:
        try:
            import requests
            r = requests.get(f"{FACILITATOR_URL}/session/{session_id}", timeout=10)
            return (r.text, r.status_code, r.headers.items())
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    return jsonify({"error": "no on-chain backend configured"}), 503


# On-chain deployment metadata for the frontend. Single source of truth is
# onchain.get_deployment(), which reads env overrides at call time so a new
# deployer only needs to export the relevant *_ADDRESS vars and restart.
@app.route("/api/onchain/info")
def api_onchain_info():
    from onchain import get_deployment
    return jsonify(get_deployment())


# /config.js - populates window.AGENTHIRE_CHAIN + window.AGENTHIRE_ADDRESSES
# from the active deployment so the frontend never carries hardcoded addresses.
# Loaded in base.html BEFORE static/js/contracts.js (which now only ships ABIs).
@app.route("/config.js")
def config_js():
    import json
    from flask import Response
    from onchain import get_deployment
    d = get_deployment()
    js = (
        "// Auto-generated from server env. Do not edit.\n"
        "window.AGENTHIRE_CHAIN = " + json.dumps({
            "chainId":    d["chainId"],
            "chainIdHex": d["chainIdHex"],
            "name":       d["chain"],
            "rpcUrl":     d["rpcUrl"],
            "explorer":   d["explorer"],
            "nativeCurrency": {"name": "AVAX", "symbol": "AVAX", "decimals": 18},
        }) + ";\n"
        "window.AGENTHIRE_ADDRESSES = " + json.dumps(d["contracts"]) + ";\n"
    )
    return Response(js, mimetype="application/javascript")


# ── REST Agent API ─────────────────────────────────────────────────────────────

@app.route("/api/agents")
def api_agents():
    """Paginated, filterable agent list."""
    category  = request.args.get("category", "")
    use_case  = request.args.get("use_case", "")
    verified  = request.args.get("verified", "")
    q         = request.args.get("q", "").lower()
    page      = max(1, int(request.args.get("page", 1)))
    per_page  = min(50, int(request.args.get("per_page", 12)))

    agents = AGENTS[:]
    if q:
        agents = [a for a in agents if q in a["name"].lower() or q in a["description"].lower()
                  or any(q in t for t in a["tags"])]
    if category:
        agents = [a for a in agents if a["category"] == category]
    if use_case:
        agents = [a for a in agents if a["use_case"] == use_case]
    if verified == "true":
        agents = [a for a in agents if a["verified"]]
    elif verified == "false":
        agents = [a for a in agents if not a["verified"]]

    total   = len(agents)
    start   = (page - 1) * per_page
    agents  = agents[start:start + per_page]
    return jsonify({"agents": agents, "total": total, "page": page, "per_page": per_page})


@app.route("/api/agents/<int:agent_id>")
def api_agent(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return jsonify({"error": "agent not found"}), 404
    return jsonify(agent)


@app.route("/api/agents/register", methods=["POST"])
def api_agents_register():
    """Register a new agent on-chain via AgentRegistry.registerAgent."""
    payload = request.get_json(silent=True) or {}
    required = ["wallet", "name", "endpointURL"]
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    oc = _get_onchain()
    if oc:
        try:
            result = oc.register_agent(payload["wallet"], payload["name"], payload["endpointURL"])
            return jsonify(result), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({
        "agentId": None,
        "status": "mock_registered",
        "note": "No FACILITATOR_PRIVATE_KEY - registration not sent on-chain.",
    }), 201


# ── On-chain agent reads ────────────────────────────────────────────────────────

@app.route("/api/agents/<int:agent_id>/reputation")
def api_agent_reputation(agent_id):
    # Prefer the DB-backed OnchainProfile — these are the agents the UI knows
    # about. Fall through to live chain reads only when no profile exists yet
    # (e.g. after real on-chain registration but before local sync).
    from simulation import get_credit_profile
    data = get_credit_profile(agent_id)
    if data is not None:
        return jsonify(data)
    oc = _get_onchain()
    if oc:
        try:
            return jsonify(oc.get_credit_profile(agent_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    return jsonify({"error": "not found"}), 404


@app.route("/api/agents/<int:agent_id>/stake")
def api_agent_stake(agent_id):
    from simulation import get_stake
    data = get_stake(agent_id)
    if data is not None:
        return jsonify(data)
    oc = _get_onchain()
    if oc:
        try:
            return jsonify(oc.get_stake(agent_id))
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    return jsonify({"error": "not found"}), 404


@app.route("/api/agents/<int:agent_id>/profile")
def api_agent_profile(agent_id):
    """Full on-chain profile — rep + stake + recent activity in one call."""
    from simulation import get_full_profile
    data = get_full_profile(agent_id)
    if data is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)


@app.route("/api/agents/<int:agent_id>/price-history")
def api_agent_price_history(agent_id):
    from simulation import get_price_history
    try:
        hours = min(168, max(1, int(request.args.get("hours", 24))))
    except ValueError:
        hours = 24
    return jsonify({"agentId": agent_id, "hours": hours, "points": get_price_history(agent_id, hours)})


@app.route("/api/agents/<int:agent_id>/transactions")
def api_agent_transactions(agent_id):
    from simulation import get_transactions
    try:
        limit = min(200, max(1, int(request.args.get("limit", 25))))
    except ValueError:
        limit = 25
    kinds_raw = request.args.get("kinds")
    kinds = [k for k in (kinds_raw.split(",") if kinds_raw else []) if k]
    return jsonify({
        "agentId": agent_id,
        "transactions": get_transactions(agent_id=agent_id, kinds=kinds or None, limit=limit),
    })


@app.route("/api/transactions")
def api_transactions():
    """Global on-chain activity feed across all agents."""
    from simulation import get_transactions
    try:
        limit = min(200, max(1, int(request.args.get("limit", 50))))
    except ValueError:
        limit = 50
    kinds_raw = request.args.get("kinds")
    kinds = [k for k in (kinds_raw.split(",") if kinds_raw else []) if k]
    return jsonify({"transactions": get_transactions(kinds=kinds or None, limit=limit)})


@app.route("/api/pricing/quote/<int:agent_id>")
def api_pricing_quote(agent_id):
    """
    Surge-adjusted quote for a single agent. Callers can pass explicit
    utilization/demand; otherwise the latest simulated PricePoint is used.
    """
    from models import Agent as AgentModel, PricePoint
    from simulation import current_price
    agent_row = AgentModel.query.get(agent_id)
    if not agent_row:
        return jsonify({"error": "not found"}), 404
    try:
        util = float(request.args.get("utilization")) if request.args.get("utilization") else None
        demand = float(request.args.get("demand")) if request.args.get("demand") else None
    except ValueError:
        util = demand = None
    if util is None or demand is None:
        latest = (
            PricePoint.query.filter_by(agent_id=agent_id)
            .order_by(PricePoint.ts.desc()).first()
        )
        if latest:
            util = util if util is not None else latest.utilization
            demand = demand if demand is not None else min(1.0, latest.utilization + 0.05)
    util = util if util is not None else 0.4
    demand = demand if demand is not None else 0.4
    return jsonify(current_price(agent_row, utilization=util, demand=demand))


# ── Escrow session management ───────────────────────────────────────────────────

@app.route("/api/session/<session_id>/cancel", methods=["POST"])
def api_session_cancel(session_id):
    try:
        sid = int(session_id)
    except ValueError:
        return jsonify({"error": "session id must be numeric"}), 400

    oc = _get_onchain()
    if oc:
        try:
            return jsonify(oc.cancel_session(sid))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    if FACILITATOR_URL:
        try:
            import requests as _req
            r = _req.post(f"{FACILITATOR_URL}/session/{session_id}/cancel", timeout=15)
            return (r.text, r.status_code, r.headers.items())
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    return jsonify({"error": "no on-chain backend configured"}), 503


# ── Auction market ──────────────────────────────────────────────────────────────

# In-memory auction bid store (mirrors what's on-chain when keys are set).
_AUCTION_BIDS: list = []


@app.route("/api/auctions")
def api_auctions():
    """Return open (not settled, not cancelled, not expired) bids."""
    now = int(__import__("time").time())
    open_bids = [
        b for b in _AUCTION_BIDS
        if not b.get("settled") and not b.get("cancelled") and b.get("expiresAt", 0) > now
    ]
    return jsonify({"bids": open_bids, "total": len(open_bids)})


@app.route("/api/auctions/<bid_id>")
def api_auction_bid(bid_id):
    # Try on-chain first
    oc = _get_onchain()
    if oc:
        try:
            return jsonify(oc.get_bid(int(bid_id)))
        except Exception as e:
            return jsonify({"error": str(e)}), 502
    # Fall back to in-memory store
    bid = next((b for b in _AUCTION_BIDS if str(b.get("bidId")) == str(bid_id)), None)
    if not bid:
        return jsonify({"error": "bid not found"}), 404
    return jsonify(bid)


@app.route("/api/auctions/bid", methods=["POST"])
def api_auction_post_bid():
    from models import AuctionBid
    payload = request.get_json(silent=True) or {}
    required = ["depositAmount", "tokenBudget", "maxPricePerToken", "categoryId", "minTier", "expiresAt"]
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    oc = _get_onchain()
    if oc and oc.facilitator:
        try:
            result = oc.post_bid(
                int(payload["depositAmount"]),
                int(payload["tokenBudget"]),
                int(payload["maxPricePerToken"]),
                int(payload["categoryId"]),
                int(payload["minTier"]),
                int(payload["expiresAt"]),
            )
            bid = AuctionBid(
                on_chain_bid_id=result.get("bidId"),
                deposit_amount=int(payload["depositAmount"]),
                token_budget=int(payload["tokenBudget"]),
                max_price_per_token=int(payload["maxPricePerToken"]),
                category_id=int(payload["categoryId"]),
                min_tier=int(payload["minTier"]),
                expires_at=int(payload["expiresAt"]),
                tx_hash=result.get("txHash"),
            )
            db.session.add(bid)
            db.session.commit()
            return jsonify(result), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Mock path - persist to DB so bids survive restarts
    bid = AuctionBid(
        deposit_amount=int(payload["depositAmount"]),
        token_budget=int(payload["tokenBudget"]),
        max_price_per_token=int(payload["maxPricePerToken"]),
        category_id=int(payload["categoryId"]),
        min_tier=int(payload["minTier"]),
        expires_at=int(payload["expiresAt"]),
    )
    db.session.add(bid)
    db.session.commit()
    return jsonify({**bid.to_dict(), "status": "mock_posted",
                    "note": "mock - FACILITATOR_PRIVATE_KEY not set"}), 201


@app.route("/api/auctions/<bid_id>/cancel", methods=["POST"])
def api_auction_cancel_bid(bid_id):
    oc = _get_onchain()
    if oc and oc.facilitator:
        try:
            result = oc.cancel_bid(int(bid_id))
            # Update in-memory store
            for b in _AUCTION_BIDS:
                if str(b.get("bidId")) == str(bid_id):
                    b["cancelled"] = True
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    for b in _AUCTION_BIDS:
        if str(b.get("bidId")) == str(bid_id):
            b["cancelled"] = True
            return jsonify({"bidId": bid_id, "status": "mock_cancelled"})
    return jsonify({"error": "bid not found"}), 404


# ── Admin action endpoints ──────────────────────────────────────────────────────

@app.route("/admin/verification-queue/<vrf_id>/approve", methods=["POST"])
@require_api_key
def admin_approve_verification(vrf_id):
    from models import VerificationEntry, Agent as AgentModel
    entry = VerificationEntry.query.get(vrf_id)
    if not entry:
        # fallback: in-memory
        entry_mem = next((v for v in VERIFICATION_QUEUE if v["id"] == vrf_id), None)
        if not entry_mem:
            return jsonify({"error": "not found"}), 404
        entry_mem["status"] = "approved"
        if entry_mem.get("agent_id"):
            a = next((a for a in AGENTS if a["id"] == entry_mem["agent_id"]), None)
            if a:
                a["verified"] = True
                a["verification_tier"] = entry_mem.get("tier", "basic")
        return jsonify({"id": vrf_id, "status": "approved"})
    entry.status = "approved"
    if entry.agent_id:
        ag = AgentModel.query.get(entry.agent_id)
        if ag:
            ag.verified = True
            ag.verification_tier = entry.tier
    db.session.commit()
    log.info("Verification approved: %s", vrf_id)
    return jsonify({"id": vrf_id, "status": "approved"})


@app.route("/admin/verification-queue/<vrf_id>/reject", methods=["POST"])
@require_api_key
def admin_reject_verification(vrf_id):
    from models import VerificationEntry
    entry = VerificationEntry.query.get(vrf_id)
    if not entry:
        entry_mem = next((v for v in VERIFICATION_QUEUE if v["id"] == vrf_id), None)
        if not entry_mem:
            return jsonify({"error": "not found"}), 404
        entry_mem["status"] = "rejected"
        return jsonify({"id": vrf_id, "status": "rejected"})
    entry.status = "rejected"
    db.session.commit()
    log.info("Verification rejected: %s", vrf_id)
    return jsonify({"id": vrf_id, "status": "rejected"})


@app.route("/admin/verification-queue/<vrf_id>/test-start", methods=["POST"])
@require_api_key
def admin_start_testing(vrf_id):
    from models import VerificationEntry
    entry = VerificationEntry.query.get(vrf_id)
    entry_mem = next((v for v in VERIFICATION_QUEUE if v["id"] == vrf_id), None)
    if not entry and not entry_mem:
        return jsonify({"error": "not found"}), 404
    if entry:
        entry.status = "testing"
        db.session.commit()
    if entry_mem:
        entry_mem["status"] = "testing"
    log.info("Verification testing started: %s", vrf_id)
    return jsonify({"id": vrf_id, "status": "testing"})


@app.route("/admin/verification-queue/<vrf_id>/escalate", methods=["POST"])
@require_api_key
def admin_escalate_verification(vrf_id):
    from models import VerificationEntry
    entry = VerificationEntry.query.get(vrf_id)
    entry_mem = next((v for v in VERIFICATION_QUEUE if v["id"] == vrf_id), None)
    if not entry and not entry_mem:
        return jsonify({"error": "not found"}), 404
    if entry:
        entry.status = "human_review"
        db.session.commit()
    if entry_mem:
        entry_mem["status"] = "human_review"
    log.info("Verification escalated to human review: %s", vrf_id)
    return jsonify({"id": vrf_id, "status": "human_review"})


@app.route("/admin/payouts/<pay_id>/release", methods=["POST"])
@require_api_key
def admin_release_payout(pay_id):
    from models import Payout
    p = Payout.query.get(pay_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    if p.status == "released":
        return jsonify({"error": "already released"}), 400
    p.status = "released"
    db.session.commit()
    log.info("Payout released: %s", pay_id)
    return jsonify({"id": pay_id, "status": "released"})


@app.route("/admin/payouts/<pay_id>/hold", methods=["POST"])
@require_api_key
def admin_hold_payout(pay_id):
    from models import Payout
    p = Payout.query.get(pay_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    p.status = "held"
    db.session.commit()
    log.info("Payout held: %s", pay_id)
    return jsonify({"id": pay_id, "status": "held"})


@app.route("/admin/payouts/<pay_id>/refund", methods=["POST"])
@require_api_key
def admin_refund_payout(pay_id):
    from models import Payout
    p = Payout.query.get(pay_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    p.status = "refunded"
    db.session.commit()
    log.info("Payout refunded: %s", pay_id)
    return jsonify({"id": pay_id, "status": "refunded"})


@app.route("/admin/payouts/release-all", methods=["POST"])
@require_api_key
def admin_release_all_payouts():
    from models import Payout
    pending = Payout.query.filter_by(status="pending").all()
    released_ids = []
    for p in pending:
        p.status = "released"
        released_ids.append(p.id)
    db.session.commit()
    log.info("Bulk release: %d payouts", len(released_ids))
    return jsonify({"released": released_ids, "count": len(released_ids)})


@app.route("/admin/moderation/<rpt_id>/resolve", methods=["POST"])
@require_api_key
def admin_resolve_report(rpt_id):
    from models import ModerationReport
    r = ModerationReport.query.get(rpt_id)
    if not r:
        return jsonify({"error": "not found"}), 404
    data = request.get_json(silent=True) or {}
    r.status = "resolved"
    notes = data.get("notes", "").strip()
    if notes:
        r.notes = notes
    db.session.commit()
    log.info("Moderation report resolved: %s", rpt_id)
    return jsonify({"id": rpt_id, "status": "resolved"})


@app.route("/admin/moderation/<rpt_id>/investigate", methods=["POST"])
@require_api_key
def admin_investigate_report(rpt_id):
    from models import ModerationReport
    r = ModerationReport.query.get(rpt_id)
    if not r:
        return jsonify({"error": "not found"}), 404
    r.status = "investigating"
    db.session.commit()
    log.info("Moderation report under investigation: %s", rpt_id)
    return jsonify({"id": rpt_id, "status": "investigating"})


@app.route("/admin/moderation/<rpt_id>/suspend", methods=["POST"])
@require_api_key
def admin_suspend_agent(rpt_id):
    from models import ModerationReport, Agent as AgentModel
    r = ModerationReport.query.get(rpt_id)
    if not r:
        return jsonify({"error": "not found"}), 404
    r.status = "suspended"
    if r.agent_id:
        ag = AgentModel.query.get(r.agent_id)
        if ag:
            ag.verified = False
            ag.verification_tier = "suspended"
        # mirror in in-memory list so marketplace reflects the suspension
        for a in AGENTS:
            if a["id"] == r.agent_id:
                a["verified"] = False
                a["verification_tier"] = "suspended"
    db.session.commit()
    log.info("Agent suspended via moderation report: %s", rpt_id)
    return jsonify({"id": rpt_id, "status": "suspended", "agent": r.agent})


# ── Order management ─────────────────────────────────────────────────────────

def _find_order(order_id):
    """Locate an order in-memory first, then fall back to DB. Returns (mem_dict_or_None, db_row_or_None)."""
    from models import Order as OrderModel
    mem = next((o for o in ORDERS if o["id"] == order_id), None)
    row = OrderModel.query.get(order_id)
    return mem, row


@app.route("/api/orders/<order_id>/complete", methods=["POST"])
def api_order_complete(order_id):
    """Mark an order complete and release escrow. Updates status in DB and in-memory."""
    mem, row = _find_order(order_id)
    if not mem and not row:
        return jsonify({"error": "order not found"}), 404
    current = (mem or {}).get("status") or (row.status if row else "")
    if current not in ("in_escrow", "in_progress"):
        return jsonify({"error": f"order is already {current}"}), 400
    if mem:
        mem["status"] = "completed"
    if row:
        row.status = "completed"
        db.session.commit()
    log.info("Order %s marked complete", order_id)
    return jsonify({"orderId": order_id, "status": "completed",
                    "message": "Escrow released. Seller has been paid."})


@app.route("/api/orders/<order_id>/start", methods=["POST"])
def api_order_start(order_id):
    """Seller marks an escrowed order as 'in_progress' to begin execution."""
    mem, row = _find_order(order_id)
    if not mem and not row:
        return jsonify({"error": "order not found"}), 404
    current = (mem or {}).get("status") or (row.status if row else "")
    if current != "in_escrow":
        return jsonify({"error": f"order cannot start from state '{current}'"}), 400
    if mem:
        mem["status"] = "in_progress"
    if row:
        row.status = "in_progress"
        db.session.commit()
    log.info("Order %s started by seller", order_id)
    return jsonify({"orderId": order_id, "status": "in_progress"})


# ── Rating API ─────────────────────────────────────────────────────────────────

@app.route("/api/agents/<int:agent_id>/rate", methods=["POST"])
def api_rate_agent(agent_id):
    payload = request.get_json(silent=True) or {}
    rating = payload.get("rating")
    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"error": "rating must be between 1 and 5"}), 400
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return jsonify({"error": "agent not found"}), 404
    # Weighted average: blend new rating in
    new_rating = round(
        (agent["rating"] * agent["reviews"] + int(rating)) / (agent["reviews"] + 1), 1
    )
    agent["rating"] = new_rating
    agent["reviews"] += 1
    # Persist the full review so it shows up on the agent detail page.
    try:
        from models import Review as ReviewModel
        user = payload.get("user") or "0xanon..."
        feedback = (payload.get("feedback") or "").strip()
        db.session.add(ReviewModel(
            agent_id=agent_id, user=user, rating=int(rating),
            comment=feedback, date=time.strftime("%Y-%m-%d"),
        ))
        db.session.commit()
    except Exception as e:
        log.warning("Could not persist review for agent %s: %s", agent_id, e)
    log.info("Agent %s rated %s (new avg %.1f, %d reviews)", agent_id, rating, new_rating, agent["reviews"])
    return jsonify({"agentId": agent_id, "rating": new_rating, "reviews": agent["reviews"]})


# ── Search API ──────────────────────────────────────────────────────────────────

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").lower().strip()
    if not q:
        return jsonify({"results": []})
    results = [
        {"id": a["id"], "name": a["name"], "category": a["category"],
         "description": a["description"], "rating": a["rating"],
         "verified": a["verified"], "billing": a["billing"],
         "current_price": a["current_price"]}
        for a in AGENTS
        if q in a["name"].lower() or q in a["description"].lower()
        or any(q in t for t in a["tags"])
    ]
    return jsonify({"results": results, "total": len(results), "query": q})


# ── Health / readiness ──────────────────────────────────────────────────────────

@app.route("/api/health")
def api_health():
    """Liveness probe - always returns 200 if the process is alive."""
    return jsonify({"status": "ok", "service": "agenthire", "ts": int(time.time())})


@app.route("/api/ready")
def api_ready():
    """Readiness probe - checks DB connectivity."""
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ready", "db": "ok", "ts": int(time.time())})
    except Exception as e:
        log.error("Readiness check failed: %s", e)
        return jsonify({"status": "unavailable", "db": str(e)}), 503


# ── Error handlers ──────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "internal server error"}), 500
    return render_template("500.html"), 500


# ── Live simulation engine ─────────────────────────────────────────────────────

@app.route("/sim")
def sim_dashboard():
    return render_template("sim.html")


@app.route("/api/sim/status")
def api_sim_status():
    from sim_engine import get_engine
    return jsonify(get_engine(app).status())


@app.route("/api/sim/start", methods=["POST"])
def api_sim_start():
    from sim_engine import get_engine
    started = get_engine(app).start()
    return jsonify({"started": started, **get_engine(app).status()})


@app.route("/api/sim/stop", methods=["POST"])
def api_sim_stop():
    from sim_engine import get_engine
    stopped = get_engine(app).stop()
    return jsonify({"stopped": stopped, **get_engine(app).status()})


@app.route("/api/sim/speed", methods=["POST"])
def api_sim_speed():
    from sim_engine import get_engine
    data = request.get_json(silent=True) or {}
    tick_s = float(data.get("tickRealSeconds", 2.0))
    get_engine(app).set_speed(tick_s)
    return jsonify(get_engine(app).status())


@app.route("/api/sim/events")
def api_sim_events():
    from sim_engine import get_engine
    since = int(request.args.get("since", 0))
    limit = int(request.args.get("limit", 100))
    return jsonify({
        "events": get_engine(app).events_since(since, limit),
        "status": get_engine(app).status(),
    })


# ── DB init + seed ─────────────────────────────────────────────────────────────────

def _sync_agents_from_db():
    """Rebuild the in-memory AGENTS list to match DB rows so marketplace,
    search, and detail views see the full seeded roster + any live additions."""
    from models import Agent as AgentModel
    rows = AgentModel.query.order_by(AgentModel.id).all()
    AGENTS.clear()
    for a in rows:
        AGENTS.append({
            "id": a.id, "name": a.name, "description": a.description,
            "long_description": a.long_description, "category": a.category,
            "use_case": a.use_case, "verified": a.verified,
            "verification_tier": a.verification_tier, "featured": a.featured,
            "rating": a.rating, "reviews": a.reviews, "billing": a.billing,
            "min_price": a.min_price, "max_price": a.max_price,
            "current_price": a.current_price, "surge_active": a.surge_active,
            "surge_multiplier": a.surge_multiplier, "seller": a.seller,
            "seller_rating": a.seller_rating, "tasks_completed": a.tasks_completed,
            "avg_completion_time": a.avg_completion_time,
            "tags": a.tags, "capabilities": a.capabilities,
        })


with app.app_context():
    try:
        from models import seed_db
        seed_db(app)
        from agent_pack import seed_bulk_agents
        seed_bulk_agents(app)
        from simulation import seed_simulation
        seed_simulation(app)
        _sync_agents_from_db()
        log.info("Database ready — %d agents in memory.", len(AGENTS))
    except Exception as _seed_err:
        log.warning("DB seed skipped: %s", _seed_err)


if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    try:
        from sim_engine import get_engine
        get_engine(app).start()
        log.info("Live simulation engine running.")
    except Exception as _sim_err:
        log.warning("Live sim autostart failed: %s", _sim_err)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
