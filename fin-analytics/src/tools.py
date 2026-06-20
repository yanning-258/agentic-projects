# Standard libraries
import re
import json
import os
from pathlib import Path
import base64
import mimetypes

# Third parties
import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic


# ====== env & clients ======
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

#what clients do: read keys from env by default, can also define explicitly
openai_client= OpenAI(api_key=openai_api_key)
anthropic_client = Anthropic(api_key=anthropic_api_key)
anthropic_client = Anthropic(
    base_url="http://jupyter-api-proxy.internal.dlai/rev-proxy/anthropic"
)

# ====== Asset ========
tickers = []


# ====== helper functions ======
def print_html(code, title):
    """
    Pretty print inside a styled card
    - If is_image=True and content is string, treat as image path/url
    - If content is pandas DataFrame/Series: render as HTML table.
    - Otherwise (string/others): show as code/text in <pre><code>
    """
    #first, get html escape
    try:
        from html import escape as _escape
    except ImportError:
        _escape = lambda x: x

    def image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

def ensure_execute_python_tags(text: str) -> str:
    """Normalize code to be wrapped in <execute_python>...</execute_python>."""
    text = text.strip()
    # Strip ```python fences if present
    text = re.sub(r"^```(?:python)?\s*|\s*```$", "", text).strip() #strip off ``` backticks
    if "<execute_python>" not in text:
        text = f"<execute_python>\n{text}\n</execute_python>" #add back execute python tags
    return text

def get_response(model: str, prompt: str) -> str:
    if "claude" in model.lower() or "anthropic" in model.lower():
        # Anthropic Claude format
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        return message.content[0].text

    else:
        # Default to OpenAI format for all other models (gpt-4, o3-mini, o1, etc.)
        response = openai_client.responses.create(
            model=model,
            input=prompt,
        )
        return response.output_text

def encode_image_b64(path: str) -> tuple[str, str]:
    """Return (media_type, base64_str) for an image file path."""
    mime, _ = mimetypes.guess_type(path)
    media_type = mime or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return media_type, b64
#Why base64: APIs talk in JSON/text, JSON strings must be valid text
#cannot hold raw binary bytes, lots of byte values from image are not in valid text characters
#base64 re-encodes binary data using 64 safe, printable ASCII characters
#so can drop image safely inside a JSON string, URL or HTML attribute, wont corrupt or break parser

#mimetypes.guess_type(path)
#looks at file extension, not the actual file content
#guess MIME type from built-in lookup table
#returns (type, encoding) type e.g. ("image/png", None)
#encoding is usually none unless it is compressed e.g. .gz

#open(path, "rb")
#"r" = read, "b" = binary
#only "r" -> python reads content as text with UTF-8, this would break for image, as arbitrary binary bytes ofetn arent UTF-8
#would get UnicodeDecodeError

#Anything binary can be base64-encoded, pdf, audio, video, encrypted blobs, arbitrary fles
#base64 output is about 33% larger than the original bytes. That size increase is the tradeoff for being safely embeddable in text.

def image_anthropic_call(model_name, prompt, media_type, b64):
    """
    Call Anthropic Claude (messages.create) with text+image and return *all* text blocks concatencated.
    Adds a system message to enforce strict JSON output.
    """
    msg = anthropic_client.messages.create(
        model=model_name,
        max_tokens=2000,
        temperature=0,
        system=(
            "You are a careful assistant. Respond with a single valid JSON object"
            ""
        ),
        messages=[{
            "role": "user",
            "content": [
                {"type": "image"}, 
                {"source": {"type": "base64", 
                           "media_type":media_type, 
                           "data":b64}
                }
            ]
        }]
    )
    #anthropic returns a list of content blocks, collect all text
    parts = []
    for block in (msg.content or []):
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()
#anthropic only has one endpoint for all chat-style call: client.messages.create()
#can do plain text, multi-turn conversation, multimodal


def image_openai_call(model_name, prompt, media_type, b64):
    data_url = f"data:{media_type};base64,{b64}"
    #why this url shaped this way?
    
    response = openai_client.responses.create(
        model=model_name,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ]
            }
        ]
    )
    #openai and anthropic both use client.responses/messages.create, then specify specs inside
    #openai: this time we want to pass both text and image, so this content is a

    content = (response.output_text or "").strip() #first time see this syntax, () is just for logical operation precedence
    return content

# ====== Finance tools ======

def yfinance_tool(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="1d")

    result = {
        "Ticker": ticker.upper(),
        "Company Name": info.get("longName", ticker.upper()),
        "Current Price": info.get('currentPrice', 'N/A'),
        "Open": hist.iloc[-1]["Open"] if not hist.empty else "N/A",
        "High": hist.iloc[-1]["High"] if not hist.empty else "N/A",
        "Low": hist.iloc[-1]["Low"] if not hist.empty else "N/A",
        "Close": hist.iloc[-1]["Close"] if not hist.empty else "N/A",
        "Market Cap": info.get('marketCap', 'N/A'),
        "P/E Ratio": info.get('trailingPE', 'N/A'),
        "52w High": info.get('fiftyTwoWeekHigh', 'N/A'),
        "52w Low": info.get('fiftyTwoWeekLow', 'N/A'),
        "Sector": info.get('sector', 'N/A'),
        "Summary": info.get('longBusinessSummary', 'N/A')
    }
    return result

def financials_tool(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    income = stock.income_stmt
    balance = stock.balance_sheet

    def get_val(df, key):
        try:
            return df.loc[key].iloc[0]
        except:
            return 'N/A'

    result = {
    "Ticker": ticker.upper(),
    "Revenue": get_val(income, 'Total Revenue'),
    "Net Income": get_val(income, 'Net Income'),
    "EPS": stock.info.get('trailingEps', 'N/A'),
    "Total Debt": get_val(balance, 'Total Debt'),
    "Total Equity": get_val(balance, 'Stockholders Equity'),
    "Debt-to-Equity": stock.info.get('debtToEquity', 'N/A')
    }
    return result

def news_tool(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    news = stock.news[:5]

    if not news:
        return f"No recent news found for {ticker.upper()}"

    items = []
    for item in news:
        content = item.get('content', {})
        link =  (
            content.get('canonicalUrl',{}).get('url')
            or content.get('clickThroughUrl', {}).get('url')
            or 'N/A'
        )
        items.append({
            "Title": content.get('title', 'N/A'),
            "Summary": content.get('summary', 'N/A'),
            "Link": link
        })
    return items

# ====== static Chart tools
import matplotlib
matplotlib.use("Agg") #this is non-interactice rendering, wont try to find GUI window that is not there in this docker container
import matplotlib.pyplot as plt
from io import BytesIO
def static_chart_tool(ticker: str) -> str:
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(hist.index, hist["Close"])
    ax.set_title(f"{ticker.upper()} - 1 Year Price History")
    ax.set_xlabel("Date")
    ax.set_ylabel("Close Price")

    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode("utf-8")


# LLM chart tools
def generate_chart_code(instruction, model, img_path):
    """
    take in instruction, look into data, call anthropic image model to generate visualization chart
    """
    prompt = f"""
    You are a data visualization expert.

    Return your answer *strictly* in this format:

    <execute_python>
    #valid python code here
    </execute_python>

    Do not add explanations, only the tags and the code.

    The code should create a visualization from a DataFrame 'df' with these columns:
    (pending new schema)

    User instruction: {instruction}

    Requirements for the code:
    1. Assume the DataFrame is already loaded as 'df'.
    2. Use matplotlib for plotting.
    3. Add clear title, axis labels, and legend if needed.
    4. 

    Return ONLY the code wrapped in <execute_python> tags.
    
    """
    return get_response(model, prompt)



#reflection
def reflect_on_img_regen(
        chart_path,
        instruction,
        model_name,
        out_path_v2,
        code_v1
):
    """
    Critique the chart IMAGE and the original code against the instruction,
    then return refined matplotlib code.
    Returns (feedback, refined_code_with_tags).
    Supports OpenAI and Anthropic (Claude).
    """
    #define media type and image path
    media_type, b64 = encode_image_b64(chart_path)

    prompt = f"""
    You are a data visualization expert.
    Your task: critique the attached chart and the original code against the given instruction,
    then return improved matplotlib code.

    Original code (for context):
    {code_v1}

    OUTPUT FORMAT (STRICT):
    1) First line: a valid JSON object with ONLY the "feedback" field.
    Example: {{"feedback": "The legend is unclear and the axis labels overlap."}}

    2) After a newline, output ONLY the refined Python code wrapped in:
    <execute_python>
    ...
    </execute_python>

    3) Import all necessary libraries in the code. Don't assume any imports from the original code.

    HARD CONSTRAINTS:
    - Do NOT include Markdown, backticks, or any extra prose outside the two parts above.
    - Use pandas/matplotlib only (no seaborn).
    - Assume df already exists; do not read from files.
    - Save to '{out_path_v2}' with dpi=300.
    - Always call plt.close() at the end (no plt.show()).
    - Include all necessary import statements.
    
    IMPORTANT: The 'date' column is already a pandas datetime64 type.
    - Do NOT concatenate 'date' with 'time' using string operations.
    - To filter by year/quarter, use: df[df['year'] == 2024] or df['date'].dt.year == 2024
    - The 'quarter' and 'year' columns already exist as integers; use them directly.

    Schema (columns available in df):
    (pending new schema)
    CRITICAL TYPE RULE: 'date' is already datetime64.
    - NEVER do: df['date'] + ' ' + df['time']  ← this will crash
    - ALWAYS filter by year/quarter using the integer columns: df[df['year'] == 2024]

    Instruction:
    {instruction}
    """

    #1. call image generation tools, claude or openai
    lower = model_name.lower()
    if "claude" in lower or "anthropic" in lower:
        content = image_anthropic_call()
    else:
        content = image_openai_call
    
    #2. parse the image-gen code returned from the model
    lines = content.strip().splitlines()
    json_line = lines[0].strip() if lines else ""

    try:
        obj = json.loads(json_line)
    except Exception as e:
        #fallback, try to capture the first {...} in all the content
        m_json = re.search(r"\{.*?\}", content, flags=re.DOTALL)
        if m_json:
            try:
                obj = json.loads(m_json.group(0))
            except Exception as e2:
                obj = {"feedback": f"Failed to parse JSON: {e2}", "refined_code": ""}
        else:
            obj = {"feedback": f"Failed to find JSON: {e}", "refined_code": ""}
        
    # --- Extract refined code from <execute_python>...</execute_python> ---
    m_code = re.search(r"<execute_python>([\s\S]*?)</execute_python>", content)
    refined_code_body = m_code.group(1).strip() if m_code else ""
    refined_code = ensure_execute_python_tags(refined_code_body)

    feedback = str(obj.get("feedback", "")).strip()
    return feedback, refined_code

