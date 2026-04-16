from flask import Flask, render_template, request, jsonify, redirect, url_for
import random

app = Flask(__name__)
app.jinja_env.globals['enumerate'] = enumerate

# ── Mock Data ──────────────────────────────────────────────────────────────────

CATEGORIES = ["Development", "Data & Analytics", "Content", "Finance", "Research", "Security", "Automation"]
USE_CASES  = ["Code Review", "Translation", "Summarization", "Trading", "Web Scraping", "Image Generation", "Testing"]

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
        "subagent_range_label": "$0.003 – $0.018",
        "total_range_label":    "$0.009 – $0.024",
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
                "summary": "Parsed your code — detected Python, 14 files, 2,840 tokens.",
            },
            {
                "id": "reason",   "order": 2, "type": "internal",  "conditional": False,
                "name": "Reasoning Engine",
                "exec_label": "Analysing code patterns",
                "purpose": "Applies OWASP rules, static analysis heuristics, and pattern matching against known vulnerability signatures.",
                "detail": "Checks 300+ rule patterns. Scores each finding by severity (Critical / High / Med / Low). Flags code paths for sub-agent escalation.",
                "summary": "Found 3 potential issues — escalating 2 for deep scan.",
            },
            {
                "id": "secure",   "order": 3, "type": "subagent",  "conditional": True,
                "name": "SecureAudit AI",
                "exec_label": "Running deep vulnerability scan",
                "purpose": "Sub-agent. Runs CVE database matching and smart contract safety checks when security issues are flagged.",
                "detail": "Called only if Reasoning Engine flags security-severity findings. Adds 15–90s to execution time. Billed separately.",
                "summary": "Confirmed 2 high-severity vulnerabilities — SQL injection (line 142), unvalidated auth input.",
            },
            {
                "id": "format",   "order": 4, "type": "internal",  "conditional": False,
                "name": "Output Formatter",
                "exec_label": "Compiling your report",
                "purpose": "Structures findings into a prioritised report with severity ratings, code snippets, and remediation steps.",
                "detail": "Outputs: executive summary, per-issue breakdown, diff-ready patches, and a machine-readable JSON manifest.",
                "summary": "Report compiled — 3 issues, 2 high, 1 medium. PDF and JSON available.",
            },
        ],
    },
    4: {  # AlphaTrader AI
        "composable": True,
        "stage_count": 4,
        "workflow_label": "4-stage signal pipeline",
        "workflow_summary": "Ingests market data → calls ResearchBot Pro for macro context → calls FinanceGPT for portfolio modeling → generates final signal set.",
        "trigger_rules": [
            {"condition": "Always — macro context required", "calls": "ResearchBot Pro", "trigger": "automatic"},
            {"condition": "Portfolio analysis requested",    "calls": "FinanceGPT",      "trigger": "automatic"},
        ],
        "sub_agents": [
            {"id": 6,  "name": "ResearchBot Pro", "role": "Market & macro research",   "billing": "per_token", "est_cost_low": 0.02, "est_cost_high": 0.08, "verified": True},
            {"id": 11, "name": "FinanceGPT",      "role": "Portfolio & DCF modeling",  "billing": "per_minute","est_cost_low": 0.10, "est_cost_high": 0.25, "verified": True},
        ],
        "base_cost_label":      "$0.45000 / min",
        "subagent_range_label": "$0.12 – $0.33",
        "total_range_label":    "$0.57 – $0.78 / min",
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
                "summary": "Ingested 90 days of BTC/ETH data — 129,600 candles across 3 exchanges.",
            },
            {
                "id": "research", "order": 2, "type": "subagent",  "conditional": False,
                "name": "ResearchBot Pro",
                "exec_label": "Gathering macro research",
                "purpose": "Sub-agent. Always called — provides macro context, news sentiment, and on-chain metrics.",
                "detail": "Queries 40+ news sources and on-chain analytics. Outputs a sentiment score and key macro flags that feed the signal model.",
                "summary": "Macro: bearish sentiment (score −0.34). Key flag: Fed rate decision in 3 days.",
            },
            {
                "id": "model",    "order": 3, "type": "subagent",  "conditional": True,
                "name": "FinanceGPT",
                "exec_label": "Running portfolio model",
                "purpose": "Sub-agent. Called when portfolio analysis is requested. Runs DCF and correlation analysis.",
                "detail": "Builds a correlation matrix across your holdings, runs Monte Carlo simulation (10k paths), outputs VaR at 95% and 99% confidence.",
                "summary": "Portfolio VaR (95%): $1,240. Correlation risk: BTC/ETH at 0.87 — consider hedging.",
            },
            {
                "id": "signal",   "order": 4, "type": "internal",  "conditional": False,
                "name": "Signal Generator",
                "exec_label": "Generating trade signals",
                "purpose": "Combines market data, macro context, and portfolio state to produce final buy/sell signals with confidence scores.",
                "detail": "Ensemble of LSTM, momentum, and mean-reversion models. Each signal includes entry price, stop-loss, take-profit, and confidence %.",
                "summary": "Generated 4 signals — 2 long BTC, 1 short ETH, 1 hold. Avg confidence: 73%.",
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
        "subagent_range_label": "$0.03 – $0.09",
        "total_range_label":    "$0.21 – $0.27 / min",
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
                "purpose": "Assesses the data source — CSV, endpoint, or database — and determines if external acquisition is needed.",
                "detail": "Validates schema, detects column types, checks for nulls and outliers. Determines if external enrichment is required.",
                "summary": "Loaded Q1 sales CSV — 48,200 rows, 12 columns, 3.2% null rate detected.",
            },
            {
                "id": "crawl",    "order": 2, "type": "subagent",  "conditional": True,
                "name": "WebCrawler X",
                "exec_label": "Acquiring external data",
                "purpose": "Sub-agent. Fetches external data when the source requires web enrichment.",
                "detail": "Renders JS pages, handles pagination and rate limiting. Outputs structured JSON ready for merge with your dataset.",
                "summary": "Scraped 240 competitor pricing records — merged with your dataset.",
            },
            {
                "id": "context",  "order": 3, "type": "subagent",  "conditional": True,
                "name": "ResearchBot Pro",
                "exec_label": "Gathering domain context",
                "purpose": "Sub-agent. Provides industry benchmarks and domain knowledge to interpret your data accurately.",
                "detail": "Queries industry reports and publishes domain averages. Outputs a context layer that improves anomaly detection accuracy.",
                "summary": "Added retail sector benchmarks — identified 14% above-average churn signal.",
            },
            {
                "id": "analyse",  "order": 4, "type": "internal",  "conditional": False,
                "name": "Analysis Engine",
                "exec_label": "Running analysis pipeline",
                "purpose": "Runs statistical modelling, anomaly detection, and chart generation on the combined dataset.",
                "detail": "Applies EDA, regression, clustering (k-means), and time-series decomposition. Outputs executive summary + downloadable charts.",
                "summary": "Analysis complete — 6 key insights, 3 anomalies flagged, 8 charts generated.",
            },
        ],
    },
    7: {  # SecureAudit AI
        "composable": True,
        "stage_count": 4,
        "workflow_label": "4-stage security audit",
        "workflow_summary": "Runs static analysis via CodeReview Pro first → performs deep security scan → generates prioritised vulnerability report.",
        "trigger_rules": [
            {"condition": "Always — static analysis required first", "calls": "CodeReview Pro", "trigger": "automatic"},
        ],
        "sub_agents": [
            {"id": 1, "name": "CodeReview Pro", "role": "Initial static analysis pass", "billing": "per_token", "est_cost_low": 0.004, "est_cost_high": 0.010, "verified": True},
        ],
        "base_cost_label":      "$0.01500 / token",
        "subagent_range_label": "$0.004 – $0.010",
        "total_range_label":    "$0.019 – $0.025",
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
                "summary": "Parsed ERC-20 contract — 847 lines, 12 functions, 3 external call sites detected.",
            },
            {
                "id": "static",   "order": 2, "type": "subagent",  "conditional": False,
                "name": "CodeReview Pro",
                "exec_label": "Running static analysis",
                "purpose": "Sub-agent. Always called — provides code quality pass and flags structural issues before deep security scan.",
                "detail": "Checks code style, gas optimisation opportunities, and basic logic errors. Results are passed to the vulnerability scanner as annotated context.",
                "summary": "Static analysis complete — 2 gas inefficiencies, 1 logic warning passed to scanner.",
            },
            {
                "id": "scan",     "order": 3, "type": "internal",  "conditional": False,
                "name": "Vulnerability Scanner",
                "exec_label": "Scanning for vulnerabilities",
                "purpose": "Matches the annotated contract against CVE database and known DeFi exploit patterns (reentrancy, flash loan attacks, etc.).",
                "detail": "Runs 180+ security checks including reentrancy, integer overflow, access control, oracle manipulation, and front-running vectors.",
                "summary": "Scan complete — 1 critical (reentrancy in withdraw()), 1 high (missing access control).",
            },
            {
                "id": "report",   "order": 4, "type": "internal",  "conditional": False,
                "name": "Report Compiler",
                "exec_label": "Compiling audit report",
                "purpose": "Generates a prioritised audit report with issue severity, code location, exploit scenario, and recommended fix.",
                "detail": "Output includes: executive summary, per-finding breakdown with PoC exploit snippets, diff-ready patches, and a machine-readable SARIF file.",
                "summary": "Audit report compiled — 2 findings, remediation patches generated.",
            },
        ],
    },
}

# Standalone agents (no A2A) — simple 3-stage workflow
def _standalone_stages(agent_name):
    return [
        {
            "id": "parse",   "order": 1, "type": "internal", "conditional": False,
            "name": "Input Parser",
            "exec_label": "Parsing your request",
            "purpose": "Validates and normalises the input — detects task type, format, and required output structure.",
            "detail": "Handles text, files, and structured data. Extracts task intent and maps to internal processing parameters.",
            "summary": "Input parsed — task type detected, parameters extracted.",
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
            "summary": "Output formatted and quality-checked — ready for delivery.",
        },
    ]

STANDALONE = {
    "composable": False,
    "stage_count": 3,
    "workflow_label": "3-stage standalone pipeline",
    "workflow_summary": "This agent operates independently. It does not call other agents.",
    "trigger_rules": [],
    "sub_agents": [],
    "base_cost_label": "—",
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

@app.route("/")
def index():
    featured = [a for a in AGENTS if a["featured"]]
    return render_template("index.html", featured=featured, stats={
        "total_agents": len(AGENTS),
        "tasks_completed": sum(a["tasks_completed"] for a in AGENTS),
        "usdc_settled": 142830,
    })

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
    reviews = [
        {"user": "0x3a4b...5c", "rating": 5, "comment": "Incredibly fast and accurate. Saved our team hours of manual review.", "date": "Apr 12, 2026"},
        {"user": "0x7f8e...2a", "rating": 4, "comment": "Great results, surge pricing was a bit steep during peak hours.", "date": "Apr 10, 2026"},
        {"user": "0x1d2e...9f", "rating": 5, "comment": "Best agent on the marketplace for this use case. Highly recommend.", "date": "Apr 8, 2026"},
    ]
    a2a = A2A_WORKFLOWS.get(agent_id, {**STANDALONE, "stages": _standalone_stages(agent["name"])})
    return render_template("agent_detail.html", agent=agent, reviews=reviews, a2a=a2a)

@app.route("/checkout/<int:agent_id>")
def checkout(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return redirect(url_for("marketplace"))
    a2a = A2A_WORKFLOWS.get(agent_id, {**STANDALONE, "stages": _standalone_stages(agent["name"])})
    return render_template("checkout.html", agent=agent, a2a=a2a)

@app.route("/order/<order_id>")
def order_detail(order_id):
    order = next((o for o in ORDERS if o["id"] == order_id), ORDERS[0])
    agent = next((a for a in AGENTS if a["id"] == order["agent_id"]), AGENTS[0])
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
    my_agents = AGENTS[:3]
    return render_template("seller/dashboard.html", agents=my_agents, orders=ORDERS, earnings=EARNINGS_DATA)

@app.route("/seller/create")
def seller_create():
    return render_template("seller/create.html", categories=CATEGORIES, use_cases=USE_CASES)

@app.route("/seller/verification")
def seller_verification():
    my_queue = VERIFICATION_QUEUE[:3]
    return render_template("seller/verification.html", queue=my_queue)

@app.route("/seller/orders")
def seller_orders():
    return render_template("seller/orders.html", orders=ORDERS)

@app.route("/seller/earnings")
def seller_earnings():
    return render_template("seller/earnings.html", earnings=EARNINGS_DATA)

# ── Admin ──────────────────────────────────────────────────────────────────────

@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin/dashboard.html", stats=ADMIN_STATS, agents=AGENTS)

@app.route("/admin/verification-queue")
def admin_verification_queue():
    return render_template("admin/verification_queue.html", queue=VERIFICATION_QUEUE)

@app.route("/admin/moderation")
def admin_moderation():
    reports = [
        {"id": "RPT-001", "agent": "WebCrawler X", "reporter": "0x1a2b...3c", "reason": "Excessive scraping causing rate limits", "date": "Apr 14, 2026", "status": "open"},
        {"id": "RPT-002", "agent": "ContentForge", "reporter": "0x4d5e...6f", "reason": "Output quality below advertised level", "date": "Apr 13, 2026", "status": "investigating"},
        {"id": "RPT-003", "agent": "AutoDoc AI", "reporter": "0x7g8h...9i", "reason": "Incorrect documentation generated", "date": "Apr 12, 2026", "status": "resolved"},
    ]
    return render_template("admin/moderation.html", reports=reports)

@app.route("/admin/payouts")
def admin_payouts():
    payouts = [
        {"id": "PAY-001", "seller": "DevTools Inc", "agent": "CodeReview Pro", "amount": 1240.50, "status": "pending", "date": "Apr 15, 2026"},
        {"id": "PAY-002", "seller": "QuantEdge Labs", "agent": "AlphaTrader AI", "amount": 3820.00, "status": "pending", "date": "Apr 15, 2026"},
        {"id": "PAY-003", "seller": "LinguaAI", "agent": "TranslateFlow", "amount": 540.20, "status": "released", "date": "Apr 14, 2026"},
        {"id": "PAY-004", "seller": "AuditShield", "agent": "SecureAudit AI", "amount": 2100.00, "status": "released", "date": "Apr 14, 2026"},
        {"id": "PAY-005", "seller": "CrawlTech", "agent": "WebCrawler X", "amount": 180.00, "status": "held", "date": "Apr 13, 2026"},
    ]
    return render_template("admin/payouts.html", payouts=payouts, stats=ADMIN_STATS)

# ── API (mock) ─────────────────────────────────────────────────────────────────

@app.route("/api/price/<int:agent_id>")
def api_price(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return jsonify({"error": "not found"}), 404
    base = agent["current_price"]
    jitter = random.uniform(-0.0005, 0.0005)
    price  = max(agent["min_price"], min(agent["max_price"], base + jitter))
    return jsonify({
        "price": round(price, 5),
        "surge": agent["surge_active"],
        "multiplier": agent["surge_multiplier"],
    })

# ── x402 / on-chain integration ────────────────────────────────────────────────
# Stub endpoint for the frontend x402 flow. In production this forwards
# the signed EIP-3009 permit to the backend facilitator service which:
#   1. calls MockUSDC.transferWithAuthorization(...)
#   2. calls EscrowPayment.depositFunds(...)
# and returns a sessionId. For the mockup we accept the signed payload and
# return a deterministic pretend session id so the UI flow can be demo'd end-to-end.
#
# Wire this to the real backend by setting FACILITATOR_URL to the backend-ref
# server (see ai-agent-marketplace/backend-ref/example-agent-server.js).
import os
import uuid
FACILITATOR_URL = os.environ.get("FACILITATOR_URL")

@app.route("/api/x402/pay", methods=["POST"])
def api_x402_pay():
    payload = request.get_json(silent=True) or {}
    required = ["from", "to", "value", "validBefore", "nonce", "v", "r", "s", "agentId"]
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    if FACILITATOR_URL:
        try:
            import requests
            r = requests.post(f"{FACILITATOR_URL}/x402/execute", json=payload, timeout=30)
            return (r.text, r.status_code, r.headers.items())
        except Exception as e:
            return jsonify({"error": f"facilitator unreachable: {e}"}), 502

    # Mockup fallback — pretend the payment went through.
    return jsonify({
        "sessionId": str(uuid.uuid4())[:8],
        "agentId": payload["agentId"],
        "status": "mock_settled",
        "note": "FACILITATOR_URL not set; this is a mock response. Point FACILITATOR_URL at the backend-ref server to wire real on-chain settlement.",
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

    # Mock path: log and accept without signing
    print(f"[dispute] agent={payload['agentId']} sev={payload['severity']} reason={payload['reason']!r}")
    return jsonify({
        "status": "pending_review",
        "note": "GATEKEEPER_URL not set; dispute logged but no on-chain incident was signed.",
    })


# Read a live escrow session from chain via the facilitator proxy.
@app.route("/api/session/<session_id>")
def api_session(session_id):
    if not FACILITATOR_URL:
        return jsonify({"error": "FACILITATOR_URL not configured"}), 503
    try:
        import requests
        r = requests.get(f"{FACILITATOR_URL}/session/{session_id}", timeout=10)
        return (r.text, r.status_code, r.headers.items())
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# On-chain deployment metadata for the frontend. Exposed so the UI can link
# to Snowtrace without hardcoding addresses in templates.
@app.route("/api/onchain/info")
def api_onchain_info():
    return jsonify({
        "chainId": 43113,
        "chain": "Avalanche Fuji",
        "explorer": "https://testnet.snowtrace.io",
        "contracts": {
            "MockUSDC":           "0x9C49D730Dfb82B7663aBE6069B5bFe867fa34c9f",
            "AgentRegistry":      "0x6B71b84Fa3C313ccC43D63A400Ab47e6A0d4BCbB",
            "ReputationContract": "0x40ef89Ce1E248Df00AF6Dc37f96BBf92A9Bf603A",
            "StakingSlashing":    "0xfc942b4d1Eb363F25886b3F5935394BD4932B896",
            "EscrowPayment":      "0xD19990C7CB8C386fa865135Ce9706A5A37A3f2f2",
            "AuctionMarket":      "0xa7AEEca5a76bd5Cd38B15dfcC2c288d3645E53E3",
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
