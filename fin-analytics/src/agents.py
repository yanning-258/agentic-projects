import os
from openai import OpenAI
from src.finance_tools import yfinance_tool, financials_tool, news_tool

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def data_agent(ticker: str, question: str) -> str:
    raw_data = f"""
    {yfinance_tool(ticker)}
    {financials_tool(ticker)}
    {news_tool(ticker)}
    """

    #get response from open ai model
    system_prompt = "You are a financial data gatherer. Summarise the following raw financial data clearly and concisely, preserving all key numbers."
    user_prompt = f"Question: {question}\n\nRaw data:\n{raw_data}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.choices[0].message.content

def analyst_agent(data_summary: str, question: str) -> str:
    system_prompt = "You are a senior financial analyst. Given the data summary, answer the user's question and identify key risks and opportunities. Be specific and cite numbers."
    user_prompt = f"Question: {question}\n\nData summary:\n{data_summary}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content

def writer_agent(analysis: str, ticker: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a financial report writer. Draft a professional Markdown report with sections for Summary, Key Metrics, Analysis, Risks, and Conclusion."},
            {"role": "user", "content": f"Write a report for {ticker.upper()} based on this analysis:\n\n{analysis}"}
        ]
    )
    return response.choices[0].message.content

def editor_agent(report: str, data_summary: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a financial editor. Check the report against the raw data summary for factual accuracy. Fix any numbers that don't match. Return the corrected report."},
            {"role": "user", "content": f"Data summary:\n{data_summary}\n\nReport to review:\n{report}"}
        ]
    )
    return response.choices[0].message.content
