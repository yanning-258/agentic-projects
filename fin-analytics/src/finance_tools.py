import yfinance as yf

def yfinance_tool(ticker: str) -> str:
    stock = yf.Ticker(ticker)
    info = stock.info

    return f"""
    Ticker: {ticker.upper()}
    Current Price: {info.get('currentPrice', 'N/A')}
    Market Cap: {info.get('marketCap', 'N/A')}
    P/E Ratio: {info.get('trailingPE', 'N/A')}
    52w High: {info.get('fiftyTwoWeekHigh', 'N/A')}
    52w Low: {info.get('fiftyTwoWeekLow', 'N/A')}
    Sector: {info.get('sector', 'N/A')}
    Summary: {info.get('longBusinessSummary', 'N/A')}
    """

def financials_tool(ticker: str) -> str:
    stock = yf.Ticker(ticker)
    
    income = stock.income_stmt
    balance = stock.balance_sheet

    def get_val(df, key):
        try:
            return df.loc[key].iloc[0]
        except:
            return 'N/A'

    return f"""
    Financials for {ticker.upper()}:
    Revenue: {get_val(income, 'Total Revenue')}
    Net Income: {get_val(income, 'Net Income')}
    EPS: {stock.info.get('trailingEps', 'N/A')}
    Total Debt: {get_val(balance, 'Total Debt')}
    Total Equity: {get_val(balance, 'Stockholders Equity')}
    Debt-to-Equity: {stock.info.get('debtToEquity', 'N/A')}
    """

def news_tool(ticker: str) -> str:
    stock = yf.Ticker(ticker)
    news = stock.news[:5]

    if not news:
        return f"No recent news found for {ticker.upper()}"

    items = []
    for item in news:
        content = item.get('content', {})
        title = content.get('title', 'N/A')
        summary = content.get('summary', 'N/A')
        items.append(f"- {title}\n  {summary}")

    return f"Recent news for {ticker.upper()}:\n" + "\n".join(items)
