#2 functions, planenr agent and executor agent step
import json
from openai import OpenAI
import os
import re
from src.agents import data_agent, analyst_agent, writer_agent, editor_agent

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==== Helper functions ====
def _coerce_to_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return list(val.values())
    return [str(val)]

def _ensure_contract(steps, ticker):
    first = f"Data agent: Fetch price, fundamentals, and news for {ticker}"
    last = f"Writer agent: Generate the final Markdown financial report with all findings"
    #if it is the first step, or first step init not the above one, insert first step
    if not steps or steps[0] != first:
        steps.insert(0, first)
    #if last step not in planned steps -> add last
    if steps[-1] != last:
        steps.append(last)
    return steps

# ==== the planner agent ====
def planner_agent(question: str, ticker: str) -> str:
    #define prompts here
    system_prompt = f"You are a financial analysis planner. Return a JSON array of 5-7 steps to answer the user's question about a stock. Steps should include data fetching, analysis, and report writing."
    user_prompt = f"Plan the analysis steps for: {question} about {ticker}"
    messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=1
    )
    
    #parse content from response
    content = response.choices[0].message.content
    try:
        steps = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', content, re.DOTALL)
        steps = json.loads(match.group()) if match else [content]
    
    steps = _coerce_to_list(steps)
    steps = _ensure_contract(steps, ticker)
    return steps


#==== after planning, the executor! ====
def executor_agent_step(step, ticker: str, question: str, history: list) -> str:
    context = "\n".join(history)
    
    if isinstance(step, dict):
        step_text = step.get('description') or str(step.get('step'))
    else:
        step_text = step
    
    step_lower = step_text.lower()

    if "data" in step_lower:
        result = data_agent(ticker, question)
    elif "analys" in step_lower:
        result = analyst_agent(context, question)
    elif "write" in step_lower or "draft" in step_lower or "report" in step_lower:
        result = writer_agent(context, ticker)
    elif "edit" in step_lower or "revise" in step_lower or "review" in step_lower:
        result = editor_agent(context, history[0] if history else "")
    else:
        result = analyst_agent(context, step_text)

    return result
