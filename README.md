# Autonomous Traders

## 1. Clear description about this repository

This repository is a lightweight autonomous trading and portfolio analysis project built in Python. It is designed to simulate a portfolio advisor that can:

- read trader portfolios from a local JSON account file,
- fetch stock prices and recent market history,
- calculate trend signals,
- decide whether a stock should be recommended for BUY, SELL, or HOLD,
- answer natural-language questions about a trader’s holdings and cash,
- suggest a long-term investing plan when the user asks for multi-year investment guidance,
- support a conversational agent flow through the console.

The project is built around a modular MCP (Model Context Protocol) style architecture, where each server has a specific responsibility:

- account server: manage trader data and trade execution,
- market server: fetch stock prices and histories,
- research server: analyze market trend signals,
- agent layer: orchestrate decisions and respond to user prompts.

This repo is best understood as a local prototype for a trading assistant or portfolio advisor, not a real brokerage or live trading system.

Important note:
- The system uses local JSON files instead of a database.
- It simulates trade decisions based on market trends.
- It is designed for learning, testing, portfolio reasoning, and experimenting with agent-style flows.

---

## 2. Project structure

```text
autonomous-traders/
├── .gitignore
├── .venv/
├── README.md
├── main.py
├── config.py
├── agents/
│   ├── __init__.py
│   ├── portfolio_agent.py
│   ├── researcher.py
│   └── trader_agent.py
├── client/
│   ├── __init__.py
│   └── mcp_client.py
├── data/
│   ├── accounts.json
│   ├── memory.json
│   └── ...
├── domain/
│   ├── __init__.py
│   ├── errors.py
│   └── models.py
├── repositories/
│   ├── __init__.py
│   ├── account_repository.py
│   └── memory_repository.py
├── servers/
│   ├── __init__.py
│   ├── accounts_server.py
│   ├── market_server.py
│   └── research_server.py
├── services/
│   ├── __init__.py
│   └── account_service.py
├── tests/
│   ├── __init__.py
│   ├── test_account_service.py
│   ├── test_portfolio_requests.py
│   ├── test_research_server.py
│   └── test_trader_strategy.py
└── .vscode/
```

---

## 3. Explanation of each file

### main.py
Purpose:
- application entry point.
- starts the interactive portfolio agent.
- also has a legacy batch runner (`run_all_traders`) that processes a set of predefined traders.

Why it matters:
- this is the file you run to start the project.
- in the current project, it launches the human-friendly interactive advisor flow.

---

### config.py
Purpose:
- central configuration for the project.
- stores environment-based settings.

Key contents:
- model name for Ollama-based usage,
- number of market days to fetch,
- trend threshold percentage,
- account file path,
- memory file path.

Why it matters:
- keeps settings in one place and avoids hardcoding values across modules.

---

### agents/portfolio_agent.py
Purpose:
- main user-facing conversational trading advisor.
- detects the trader name from natural-language input,
- reads the trader portfolio,
- analyzes holdings and candidate stocks,
- decides whether to produce a short-term trade recommendation or a long-term investing answer,
- uses persistence for trader and investor preference memory.

Important features:
- `normalize_trader_name()` handles prompts like “I am Trader 1”
- `extract_investor_preferences()` reads monthly contribution, time horizon, and risk profile
- `format_long_term_answer()` creates long-term portfolio guidance
- `format_recommendation_answer()` creates short-term buy/sell/hold recommendations
- `interactive_portfolio_agent()` runs the CLI conversation loop

This is the main “agent” layer that makes the project feel like an assistant instead of a plain script.

---

### agents/trader_agent.py
Purpose:
- trading decision engine.
- performs the actual stock decision process based on current market research.
- contains the strategy that enforces: buy when trend is downward, sell when trend is upward, and hold when stable.

Why it matters:
- this is the rule layer that converts market analysis into a trade action.
- it prevents ad-hoc model output from bypassing the project strategy.

---

### agents/researcher.py
Purpose:
- supporting research helper for additional analysis workflows.
- likely used to gather or prepare stock insights before trading decisions.

Why it matters:
- keeps research responsibilities separate from the main agent flow.

---

### client/mcp_client.py
Purpose:
- central MCP client used to talk to the project’s servers.
- starts each server as a subprocess using the command line,
- opens a client session,
- lists tools,
- calls tool functions remotely,
- converts MCP responses into regular Python dictionaries.

Why it matters:
- this file is the bridge between the agent and the market/account/research server modules.
- without it, the agent could not call the MCP tools reliably.

---

### servers/accounts_server.py
Purpose:
- exposes account data and trade operations as MCP tools.

Available tools:
- `get_account()`
- `execute_trade()`

Why it matters:
- this is the server that provides trader cash and holdings information to the rest of the system.

---

### servers/market_server.py
Purpose:
- gets real market data from Yahoo Finance using the `yfinance` library.
- provides:
  - latest stock price,
  - recent market history,
  - price change information.

Why it matters:
- without market data, the trend and recommendation engine has no pricing source.

---

### servers/research_server.py
Purpose:
- calculates trend patterns from recent price data.
- classifies a stock as:
  - `STRONG_UPWARD`
  - `STRONG_DOWNWARD`
  - `STABLE`

Why it matters:
- the decision engine uses this trend to produce BUY/SELL/HOLD logic.

---

### services/account_service.py
Purpose:
- contains financial validation logic for simulating account operations.

Responsibilities:
- validate stock quantity and price,
- check for insufficient cash,
- check for insufficient shares,
- execute buy/sell/hold actions,
- update holdings and cash.

Why it matters:
- this is the business-logic layer between the repository and the MCP server.

---

### repositories/account_repository.py
Purpose:
- JSON-backed persistence for account information.
- loads, validates, and saves the account dataset safely.

Why it matters:
- allows the app to store trader states without a database.

---

### repositories/memory_repository.py
Purpose:
- intended for conversational memory persistence.
- helps persist memory data separate from account state.

Why it matters:
- supports future memory features and long-running conversational context.

---

### domain/models.py
Purpose:
- defines typed domain models.

Included models:
- `TradeAction` enum
- `Account` dataclass
- `TradeRequest` dataclass

Why it matters:
- keeps business rules and data structures clean and explicit.

---

### domain/errors.py
Purpose:
- custom exceptions for invalid account/trade behavior.

Examples:
- invalid trade, insufficient cash, insufficient shares, trader not found.

Why it matters:
- ensures validation errors are handled consistently.

---

### data/accounts.json
Purpose:
- stores trader-level cash and holdings.

Example:
```json
{
  "Trader 1": {
    "cash": 9544.3,
    "holdings": {
      "AAPL": 10
    }
  }
}
```

Why it matters:
- this is the live portfolio data used by the agent during interactive analysis.

---

### data/memory.json
Purpose:
- stores current conversation context and investor preferences.
- used to remember the active trader and recent profile inputs like monthly contribution, time horizon, and risk preference.

Why it matters:
- provides persistence for long-term planning flows across multiple prompts.

---

### tests/
Purpose:
- validation suite for the project.

Included tests:
- trader strategy behavior,
- portfolio prompts and investor profile detection,
- research logic,
- account service validation.

Why it matters:
- helps ensure the project logic remains stable while extending the agent.

---

## 4. Explain the complete project with an example

### High-level workflow

The project follows this flow:

1. User enters a prompt like:
   - “I am Trader 1”
   - “I am Trader 1, which stock should I buy?”
   - “I want to invest for 10 years with medium risk”

2. `portfolio_agent.py` parses the input.
   - identifies the trader,
   - extracts profile details like time horizon and risk,
   - chooses whether to answer as a short-term trading advisor or long-term portfolio planner.

3. The system calls `accounts_server` via `mcp_client`.
   - fetches the trader’s cash and holdings from `data/accounts.json`.

4. The system calls `market_server`.
   - retrieves current stock prices.

5. The system calls `research_server`.
   - calculates the trend.

6. The trading logic decides on action.
   - upward trend → SELL
   - downward trend → BUY
   - stable trend → HOLD

7. The agent formats a natural-language response for the user.

---

### Example walkthrough

#### Example 1: short-term recommendation

Input:
```text
I am Trader 2
```

Flow:
- agent reads Trader 2 portfolio from accounts.json
- trader has cash and holdings like MSFT and AAPL
- agent checks the stock universe
- it evaluates trends and pricing
- it returns a set of recommendations like:
  - “Best buying opportunity: Salesforce(CRM) ...”
  - “Potential profit-taking opportunities: ...”
  - “Hold/watchlist names: ...”

This is a short-term tactical recommendation flow.

---

#### Example 2: long-term investment plan

Input:
```text
I am Trader 1. I want to invest for 10 years and my risk is medium.
```

Flow:
- agent detects Trader 1
- agent recognizes long-term intent
- it uses the trader’s account context and current holdings
- it explains long-term investing principles
- it may suggest a diversified portfolio with sectors and asset allocation logic
- it can mention index funds or ETFs for lower-risk planning
- it asks the user to share monthly contribution if they want a more personalized plan

This is the “portfolio advisor” style response designed for long-horizon investing.

---

#### Example 3: India-focused plan

Input:
```text
I am Trader 2. India focused plan
```

Flow:
- agent detects Trader 2
- it recognizes India-specific intent
- it explains that the current account data is US-based and should not be mixed with Indian stock data
- it provides India-sector watchlist examples like HDFC Bank, ICICI Bank, Reliance, TCS, and others
- it asks for INR amount, monthly contribution, time horizon, and risk preference to build a more personal plan

---

### Real execution example

To run the project:

```bash
cd /Users/karpurapusathvika/personal-projects/autonomout-traders
.venv/bin/python main.py
```

Then the user can type prompts like:

```text
I am Trader 1
I am Trader 1. Which stock should I buy?
I am Trader 2. I want to maintain this for long time.
My monthly contribution is 5000, time horizon is 10 years and risk is medium.
India focused plan
```

The agent responds with portfolio analysis, watchlist recommendations, and long-term guidance.

---

## Summary

This repository combines:

- a JSON-backed trader account store,
- an MCP-based market and research architecture,
- a domain service layer for trade validation,
- a conversational portfolio agent,
- a long-term investment guidance mode.

In short, this project is a local prototype of an intelligent trading assistant that can analyze current trader portfolios, reason about stock trends, and respond naturally to investment questions.

---

## Best way to use this repository

- Use it as a learning project for Python + MCP + trading logic.
- Extend it with more advanced portfolio scoring.
- Add real broker APIs, more stock universes, and an index/ETF recommendation engine.
- Add a web or chat interface later.
- Expand the research layer to include business quality, valuation, dividend history, and risk scoring.

This repo is a strong foundation for a portfolio adviser or an educational trading AI prototype.
