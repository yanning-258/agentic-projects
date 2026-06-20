"""
render result taken using tools, showcase dashboard in webpage
"""

from src.tools import yfinance_tool, financials_tool, news_tool, static_chart_tool

TICKERS = ["AAPL", "TSM", "TSLA", "HSBC", "GOOG"]

def get_ticker_dashboard(ticker: str) -> dict:
    return {
        "Ticker": ticker.upper(),
        "Snapshot": yfinance_tool(ticker),
        "Financials": financials_tool(ticker),
        "News": news_tool(ticker),
        "Chart": static_chart_tool(ticker),
    }

def get_dashboard_data(tickers: list[str] = TICKERS) -> list[dict]:
    return [get_ticker_dashboard(t) for t in tickers]
