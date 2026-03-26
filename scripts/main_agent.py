# import json
# import pandas as pd
# from dotenv import load_dotenv
# import os
# import sys
# from groq import Groq
# import re
# import plotly.io as pio
# import plotly.graph_objects as go

# from scripts.pandas_tool import PandasTool
# from scripts.visualization_tool import VisualizationTool
# from scripts.safe_executor import safe_execute

# load_dotenv()

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# DATA_PATH = os.path.join(BASE_DIR, "data")
# REGISTRY_FILE = os.path.join(DATA_PATH, "df_registry.json")
# PKL_FILE = {"orders": "orders.pkl"}

# client = Groq(api_key=os.getenv("GROQ_KEY"))

# with open(REGISTRY_FILE) as f:
#     registry = json.load(f)

# df = pd.read_pickle(os.path.join(DATA_PATH, PKL_FILE["orders"]))


# class LLMBrainAgent:
#     def __init__(self, model_name, registry, df, llm_client):
#         self.model_name = model_name
#         self.registry = registry
#         self.df = df
#         self.llm_client = llm_client
#         self.pandas_tool = PandasTool(df)
#         self.visualization_tool = VisualizationTool(df)

#         if not self.llm_client:
#             raise ValueError("LLM client not provided")

#     def is_visual_query(self, user_query):
#         visual_keywords = [
#             "chart", "plot", "graph", "visualize",
#             "bar chart", "line chart", "pie chart",
#             "draw", "show as chart", "visual representation"
#         ]
#         q = user_query.lower()
#         return any(k in q for k in visual_keywords)

#     def build_prompt(self, user_query):
#         is_visual = self.is_visual_query(user_query)
#         return f"""
# You are a data analyst AI agent.

# You have access to the following DataFrame schema:

# {json.dumps(self.registry, indent=4)}

# CRITICAL RULES:
# - Output ONLY executable Python code
# - DO NOT include words like "Reasoning", "Explanation", "Python Code"
# - DO NOT include any text before or after the code
# - ONLY include Python comments using #
# - The first line MUST be valid Python (not text)
# - Use ONLY the DataFrame 'df'
# - Assign final output to variable 'result'
# - NEVER return only a DataFrame if the user asks for a chart
# - DO NOT redefine df
# - DO NOT call any tools
# - DO NOT use markdown

# {"IMPORTANT: The user is NOT asking for a chart. DO NOT generate any plots. Return only data." if not is_visual else ""}
# {"IMPORTANT: The user is asking for a visualization. You MUST generate a Plotly chart using px." if is_visual else ""}

# PLOTTING RULES:
# - ONLY create a chart IF the user explicitly asks for:
#   "chart", "plot", "graph", "bar", "line", "pie", "visualize"
# - OTHERWISE return ONLY data (DataFrame / Series / scalar)
# - Use ONLY plotly.express (px) for charts
# - DO NOT import plotly (already available)
# - Always assign plot to: fig = px.<chart>(...)
# - Final output MUST be: result = fig
# - Do NOT combine assignments like result = fig = ...

# STRICT PLOT RULE:
# 1. Group data
# 2. Reset index
# 3. Store in a variable (df_grouped)
# 4. Use df_grouped in plot
# - You MUST always specify x=<column> and y=<column>
# - NEVER call px.bar() without x and y
# - DO NOT apply filters unless explicitly mentioned
# - DO NOT limit to top N unless asked

# Example (category groupby):
# df_grouped = df.groupby('Category')['Amount'].sum().reset_index()
# fig = px.bar(df_grouped, x='Category', y='Amount')
# result = fig

# Example (date groupby by year — ALWAYS rename columns after reset_index):
# df_grouped = df.groupby(df['Order Date'].dt.year)['Amount'].sum().reset_index()
# df_grouped.columns = ['Year', 'Amount']
# fig = px.line(df_grouped, x='Year', y='Amount')
# result = fig

# Example (date groupby by month):
# df_grouped = df.groupby(df['Order Date'].dt.to_period('M').astype(str))['Amount'].sum().reset_index()
# df_grouped.columns = ['Month', 'Amount']
# fig = px.line(df_grouped, x='Month', y='Amount')
# result = fig

# DATA RULES FOR PLOTS:
# - Always use a DataFrame (NOT a Series)
# - Always use .reset_index() after groupby
# - CRITICAL: After groupby on df['col'].dt.year or dt.month, ALWAYS rename columns:
#   df_grouped.columns = ['Year', 'Amount']  (or ['Month', 'Amount'])
#   This prevents the original datetime column name being reused with integer values.

# LOGIC RULES:
# - Follow: Filter -> groupby -> aggregate
# - Use correct column names from schema
# - Use .dt.year / .dt.to_period('M') for date grouping
# - ALWAYS rename df_grouped columns after a date-based groupby
# - DO NOT compare dates to strings

# User Question:
# {user_query}
# """

#     def query_llm(self, prompt):
#         try:
#             response = self.llm_client.chat.completions.create(
#                 model="llama-3.1-8b-instant",
#                 messages=[{"role": "user", "content": prompt}]
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"LLM Error: {str(e)}"

#     def parse_llm_output(self, llm_output):
#         reasoning, code = "", ""
#         reasoning_match = re.search(r"reasoning:(.*?)code:", llm_output, re.IGNORECASE | re.DOTALL)
#         code_match = re.search(r"code:(.*)", llm_output, re.IGNORECASE | re.DOTALL)

#         if code_match:
#             code = code_match.group(1).strip()
#         else:
#             code = llm_output.strip()
#         if reasoning_match:
#             reasoning = reasoning_match.group(1).strip()

#         code = re.sub(r"```(?:python)?\n?", "", code)
#         code = code.replace("```", "")
#         return reasoning, code

#     def fix_date_groupby(self, code):
#         """Inject column rename after dt.year/month groupby if LLM forgot it."""
#         lines = code.split("\n")
#         result_lines = []
#         for i, line in enumerate(lines):
#             result_lines.append(line)
#             next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
#             if "df_grouped" in line and "reset_index()" in line and "columns" not in line:
#                 if ".dt.year" in line and "df_grouped.columns" not in next_line:
#                     result_lines.append("df_grouped.columns = ['Year', 'Amount']")
#                 elif ".dt.month" in line and "df_grouped.columns" not in next_line:
#                     result_lines.append("df_grouped.columns = ['Month', 'Amount']")
#                 elif "to_period" in line and "df_grouped.columns" not in next_line:
#                     result_lines.append("df_grouped.columns = ['Period', 'Amount']")
#         return "\n".join(result_lines)

#     def clean_code(self, code):
#         lines = code.split("\n")
#         clean_lines = []

#         for line in lines:
#             line_strip = line.strip().lower()
#             if "import plotly" in line_strip:
#                 continue
#             if line_strip.startswith(("reasoning", "python code", "code:")):
#                 continue
#             if "pandas_tool" in line_strip or "visualization_tool" in line_strip:
#                 continue
#             if line.strip() == "":
#                 continue
#             clean_lines.append(line)

#         cleaned = "\n".join(clean_lines)
#         for i, line in enumerate(clean_lines):
#             if line.strip().startswith("#") or "df" in line:
#                 cleaned = "\n".join(clean_lines[i:])
#                 break

#         return self.fix_date_groupby(cleaned)

#     def handle_query(self, user_query):
#         prompt = self.build_prompt(user_query)
#         llm_output = self.query_llm(prompt)

#         if "LLM Error" in llm_output:
#             return {"type": "error", "error": llm_output, "code": ""}

#         reasoning, code = self.parse_llm_output(llm_output)
#         if not code:
#             return {"type": "error", "error": "Failed to extract code from LLM output", "code": ""}

#         # Check raw llm_output for px. BEFORE cleaning to avoid false retry
#         if self.is_visual_query(user_query) and "px." not in llm_output:
#             print("LLM failed to generate chart. Retrying...")
#             retry_prompt = self.build_prompt(user_query) + "\n\nREMEMBER: You MUST create a Plotly chart using px."
#             llm_output = self.query_llm(retry_prompt)
#             _, code = self.parse_llm_output(llm_output)

#         cleaned_code = self.clean_code(code)
#         if not any(x in cleaned_code for x in ["df", "result"]):
#             return {"type": "error", "error": f"Invalid code generated:\n{cleaned_code}", "code": cleaned_code}

#         is_visual = self.is_visual_query(user_query)

#         print("\n=== LLM Reasoning ===")
#         print(reasoning or "No reasoning returned")
#         print("\n=== Tool ===")
#         print("visualization_tool" if is_visual else "pandas_tool")
#         print("\n=== Generated Code ===")
#         print(cleaned_code)

#         # Execute code
#         raw = safe_execute(cleaned_code, self.df)

#         # safe_execute always returns a dict with one of three shapes:
#         #   {"error": "..."}                          -> execution/timeout error
#         #   {"type": "plotly", "data": "<json>", ...} -> Plotly figure (already JSON string)
#         #   {"type": "data",   "result": <value>, ...} -> scalar / DataFrame / Series

#         if not isinstance(raw, dict):
#             return {"type": "error", "error": f"Unexpected safe_execute output: {raw}", "code": cleaned_code}

#         if "error" in raw and raw.get("type") != "data":
#             return {"type": "error", "error": raw["error"], "code": cleaned_code}

#         if is_visual:
#             if raw.get("type") == "plotly":
#                 # data is already a JSON string from result_obj.to_json()
#                 return {"type": "chart", "result": raw["data"], "code": cleaned_code}
#             else:
#                 return {"type": "error", "error": "Chart query ran but safe_execute returned data instead of a Plotly figure. Check generated code.", "code": cleaned_code}

#         # Data result — safe_executor serializes DataFrames/Series to dicts before pickling
#         result_type = raw.get("result_type", "scalar")
#         result = raw.get("result")

#         if result_type in ("dataframe", "series"):
#             # Reconstruct from orient="split" dict: {"columns": [...], "data": [[...], ...]}
#             df_result = pd.DataFrame(
#                 data=result["data"],
#                 columns=result["columns"]
#             )
#             return {
#                 "type": "table",
#                 "columns": df_result.columns.tolist(),
#                 "rows": [[str(v) for v in row] for row in df_result.values.tolist()],
#                 "code": cleaned_code
#             }
#         else:
#             return {"type": "scalar", "result": str(result), "code": cleaned_code}


# if __name__ == "__main__":
#     agent = LLMBrainAgent(
#         model_name="llama3",
#         registry=registry,
#         df=df,
#         llm_client=client
#     )

#     while True:
#         user_query = input("\nEnter your question (or 'exit'): ")
#         if user_query.lower() in ["exit", "quit"]:
#             break
#         result = agent.handle_query(user_query)
#         print("\n=== Result ===")
#         print(result)




#from curses import raw
import json
import pandas as pd
from dotenv import load_dotenv
import os
import sys
from groq import Groq
import re
import io
import boto3
import s3fs

from scripts.pandas_tool import PandasTool
from scripts.visualization_tool import VisualizationTool
from scripts.safe_executor import safe_execute

load_dotenv()

# =========================
# S3 CLIENT
# =========================
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="ap-south-1"
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# =========================
# CONFIG
# =========================
PKL_FILE = "master.pkl"
DATE_PATTERN = r"\d{4}_\d{2}_\d{2}"

client = Groq(api_key=os.getenv("GROQ_KEY"))

# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# DATA_PATH = os.path.join(BASE_DIR, "data")
# REGISTRY_FILE = os.path.join(DATA_PATH, "df_registry.json")

# with open(REGISTRY_FILE) as f:
#     registry = json.load(f)





def get_latest_folder(bucket):
    fs = s3fs.S3FileSystem()

    folders = []
    for item in fs.ls(bucket):
        name = item.split("/")[-1]
        if re.match(DATE_PATTERN, name):
            folders.append(name)

    if not folders:
        raise Exception("No valid date folders found in S3")

    return sorted(folders, reverse=True)[0]

def load_registry_from_s3(bucket, folder):
    key = f"{folder}/df_registry.json"

    response = s3.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()

    return json.loads(body.decode("utf-8"))


latest_folder = get_latest_folder(BUCKET_NAME)

registry = load_registry_from_s3(BUCKET_NAME, latest_folder)


def load_df_from_s3(bucket, folder, file_name):
    key = f"{folder}/{file_name}"

    response = s3.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()

    return pd.read_pickle(io.BytesIO(body))


# =========================
# LOAD DATAFRAME
# =========================
latest_folder = get_latest_folder(BUCKET_NAME)
df = load_df_from_s3(BUCKET_NAME, latest_folder, PKL_FILE)

class LLMBrainAgent:
    def __init__(self, model_name, registry, df, llm_client):
        self.model_name = model_name
        self.registry = registry
        self.df = df
        self.llm_client = llm_client
        self.pandas_tool = PandasTool(df)
        self.visualization_tool = VisualizationTool(df)

        if not self.llm_client:
            raise ValueError("LLM client not provided")

    def is_visual_query(self, user_query):
        visual_keywords = [
            "chart", "plot", "graph", "visualize",
            "bar chart", "line chart", "pie chart",
            "draw", "show as chart", "visual representation"
        ]
        q = user_query.lower()
        return any(k in q for k in visual_keywords)

    def build_prompt(self, user_query):
        is_visual = self.is_visual_query(user_query)
        return f"""
You are a data analyst AI agent.

You have access to the following DataFrame schema:

{json.dumps(self.registry, indent=4)}

CRITICAL RULES:
- Output ONLY executable Python code
- DO NOT include words like "Reasoning", "Explanation", "Python Code"
- DO NOT include any text before or after the code
- ONLY include Python comments using #
- The first line MUST be valid Python (not text)
- Use ONLY the DataFrame 'df'
- Assign final output to variable 'result'
- NEVER return only a DataFrame if the user asks for a chart
- DO NOT redefine df
- DO NOT call any tools
- DO NOT use markdown

Always ensure:
- All brackets are properly closed

HARD EXECUTION RULES (VERY IMPORTANT):

1. You MUST always assign a final variable:
   result = <final_output>

2. ABSOLUTE GROUPBY SAFETY RULE (CRITICAL):

- NEVER use ANY expression inside groupby()
- groupby() MUST ONLY accept column names as STRINGS

❌ FORBIDDEN:
groupby(df['Order Date'].dt.year)
groupby(df['Order Date'].dt.to_period('M'))
groupby(df['Month'])
groupby(df['anything derived directly'])

✅ ONLY ALLOWED:
df['Year'] = df['Order Date'].dt.year
df.groupby('Year')

df['Month'] = df['Order Date'].dt.to_period('M').astype(str)
df.groupby('Month')

3. ALWAYS do this 3-step pattern for grouping:

   STEP 1: Filter with .copy() — MANDATORY
   STEP 2: Create column on the copy
   STEP 3: Group by column name (STRING ONLY)

   Example:
   df_filtered = df[df['Order Date'].dt.year == 2018].copy()  # .copy() is MANDATORY
   df_filtered['Month'] = df_filtered['Order Date'].dt.to_period('M').astype(str)
   df_grouped = df_filtered.groupby('Month')['Order ID'].count().reset_index()
   df_grouped.columns = ['Month', 'Total Orders']
   result = df_grouped

4. NEVER pass a Series into groupby()

5. If grouping by date, ALWAYS create a new column first

6. FINAL OUTPUT MUST ALWAYS BE ASSIGNED TO `result`

CRITICAL SLICE RULE:
- WHENEVER you filter a DataFrame and then add a new column to it, 
  you MUST use .copy() after the filter
- df_filtered = df[condition].copy()   ← ALWAYS
- NEVER do: df_filtered = df[condition]  ← FORBIDDEN if you add columns after

{"IMPORTANT: The user is NOT asking for a chart. DO NOT generate any plots. Return only data." if not is_visual else ""}
{"IMPORTANT: The user is asking for a visualization. You MUST generate a Plotly chart using px." if is_visual else ""}

PLOTTING RULES:
- ONLY create a chart IF the user explicitly asks for:
  "chart", "plot", "graph", "bar", "line", "pie", "visualize"
- OTHERWISE return ONLY data (DataFrame / Series / scalar)
- Use ONLY plotly.express (px) for charts
- DO NOT import plotly (already available)
- Always assign plot to: fig = px.<chart>(...)
- Final output MUST be: result = fig
- Do NOT combine assignments like result = fig = ...

STRICT PLOT RULE:
1. Group data
2. Reset index
3. Store in a variable (df_grouped)
4. Use df_grouped in plot
- You MUST always specify x=<column> and y=<column>
- NEVER call px.bar() without x and y
- DO NOT apply filters unless explicitly mentioned
- DO NOT limit to top N unless asked

Example (category groupby):
df_grouped = df.groupby('Category')['Amount'].sum().reset_index()
fig = px.bar(df_grouped, x='Category', y='Amount')
result = fig

Example (date groupby by year — ALWAYS rename columns after reset_index):
df['Year'] = df['Order Date'].dt.year
df_grouped = df.groupby('Year')['Amount'].sum().reset_index()
df_grouped.columns = ['Year', 'Amount']
fig = px.line(df_grouped, x='Year', y='Amount')
result = fig

Example (date groupby by month):
df_grouped = df.groupby(df['Order Date'].dt.to_period('M').astype(str))['Amount'].sum().reset_index()
df_grouped.columns = ['Month', 'Amount']
fig = px.line(df_grouped, x='Month', y='Amount')
result = fig

DATA RULES FOR PLOTS:
- Always use a DataFrame (NOT a Series)
- Always use .reset_index() after groupby
- CRITICAL: After groupby on df['col'].dt.year or dt.month, ALWAYS rename columns:
  df_grouped.columns = ['Year', 'Amount']  (or ['Month', 'Amount'])
  This prevents the original datetime column name being reused with integer values.

LOGIC RULES:
- Follow: Filter -> groupby -> aggregate
- Use correct column names from schema
- Use .dt.year / .dt.to_period('M') for date grouping
- ALWAYS rename df_grouped columns after a date-based groupby
- DO NOT compare dates to strings

User Question:
{user_query}
"""

    def query_llm(self, prompt):
        try:
            response = self.llm_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def parse_llm_output(self, llm_output):
        reasoning, code = "", ""
        reasoning_match = re.search(r"reasoning:(.*?)code:", llm_output, re.IGNORECASE | re.DOTALL)
        code_match = re.search(r"code:(.*)", llm_output, re.IGNORECASE | re.DOTALL)

        if code_match:
            code = code_match.group(1).strip()
        else:
            code = llm_output.strip()
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()

        code = re.sub(r"```(?:python)?\n?", "", code)
        code = code.replace("```", "")
        return reasoning, code

    def fix_date_groupby(self, code):
        """Inject column rename after dt.year/month groupby if LLM forgot it."""
        lines = code.split("\n")
        result_lines = []
        for i, line in enumerate(lines):
            result_lines.append(line)
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if "df_grouped" in line and "reset_index()" in line and "columns" not in line:
                if ".dt.year" in line and "df_grouped.columns" not in next_line:
                    result_lines.append("df_grouped.columns = ['Year', 'Amount']")
                elif ".dt.month" in line and "df_grouped.columns" not in next_line:
                    result_lines.append("df_grouped.columns = ['Month', 'Amount']")
                elif "to_period" in line and "df_grouped.columns" not in next_line:
                    result_lines.append("df_grouped.columns = ['Period', 'Amount']")
        return "\n".join(result_lines)

    def clean_code(self, code):
        lines = code.split("\n")
        clean_lines = []

        for line in lines:
            line_strip = line.strip().lower()
            if "import plotly" in line_strip:
                continue
            if line_strip.startswith(("reasoning", "python code", "code:")):
                continue
            if "pandas_tool" in line_strip or "visualization_tool" in line_strip:
                continue
            if line.strip() == "":
                continue
            clean_lines.append(line)

        cleaned = "\n".join(clean_lines)
        for i, line in enumerate(clean_lines):
            if line.strip().startswith("#") or "df" in line:
                cleaned = "\n".join(clean_lines[i:])
                break

        return self.fix_date_groupby(cleaned)

    def fix_missing_copy(self, code):
        """Inject .copy() if LLM forgot it on filtered assignments."""
        import re
        # Match: df_filtered = df[...] without .copy() at the end
        pattern = r'(df_\w+\s*=\s*df\[[^\]]+\])\s*$'
        lines = code.split('\n')
        fixed = []
        for i, line in enumerate(lines):
            # Check if next line assigns a new column to this filtered df
            next_line = lines[i+1].strip() if i+1 < len(lines) else ''
            if re.search(pattern, line.strip()) and '.copy()' not in line:
                if re.match(r'df_\w+\[', next_line):  # next line adds a column
                    line = line.rstrip() + '.copy()'
            fixed.append(line)
        return '\n'.join(fixed)

    def handle_query(self, user_query):
        prompt = self.build_prompt(user_query)
        llm_output = self.query_llm(prompt)

        if "LLM Error" in llm_output:
            return {"type": "error", "error": llm_output, "code": ""}

        reasoning, code = self.parse_llm_output(llm_output)
        if not code:
            return {"type": "error", "error": "Failed to extract code from LLM output", "code": ""}

        # Check raw llm_output for px. BEFORE cleaning to avoid false retry
        if self.is_visual_query(user_query) and "px." not in llm_output:
            print("LLM failed to generate chart. Retrying...")
            retry_prompt = self.build_prompt(user_query) + "\n\nREMEMBER: You MUST create a Plotly chart using px."
            llm_output = self.query_llm(retry_prompt)
            _, code = self.parse_llm_output(llm_output)

        cleaned_code = self.clean_code(code)
        if not any(x in cleaned_code for x in ["df", "result"]):
            return {"type": "error", "error": f"Invalid code generated:\n{cleaned_code}", "code": cleaned_code}

        is_visual = self.is_visual_query(user_query)

        print("\n=== LLM Reasoning ===")
        print(reasoning or "No reasoning returned")
        print("\n=== Tool ===")
        print("visualization_tool" if is_visual else "pandas_tool")
        print("\n=== Generated Code ===")
        print(cleaned_code)

        # Execute code
        raw = safe_execute(cleaned_code, self.df)

        # safe_execute always returns a dict with one of three shapes:
        #   {"error": "..."}                          -> execution/timeout error
        #   {"type": "plotly", "data": "<json>", ...} -> Plotly figure (already JSON string)
        #   {"type": "data",   "result": <value>, ...} -> scalar / DataFrame / Series

        if not isinstance(raw, dict):
            return {"type": "error", "error": f"Unexpected safe_execute output: {raw}", "code": cleaned_code}

        if "error" in raw:
            return {"type": "error", "error": raw["error"], "code": cleaned_code}

        if is_visual:
            if raw.get("type") == "plotly":
                # data is already a JSON string from result_obj.to_json()
                return {"type": "chart", "result": raw["result"], "code": cleaned_code}
            else:
                return {"type": "error", "error": "Chart query ran but safe_execute returned data instead of a Plotly figure. Check generated code.", "code": cleaned_code}

        # Data result — safe_executor serializes DataFrames/Series to dicts before pickling
        result_type = raw.get("result_type", "scalar")
        result = raw.get("result")

        if result_type in ("dataframe", "series"):
            # Reconstruct from orient="split" dict: {"columns": [...], "data": [[...], ...]}
            df_result = pd.DataFrame(
                data=result["data"],
                columns=result["columns"]
            )
            return {
                "type": "table",
                "columns": df_result.columns.tolist(),
                "rows": [[str(v) for v in row] for row in df_result.values.tolist()],
                "code": cleaned_code
            }
        else:
            return {"type": "scalar", "result": str(result), "code": cleaned_code}


if __name__ == "__main__":
    agent = LLMBrainAgent(
        model_name="llama3",
        registry=registry,
        df=df,
        llm_client=client
    )

    while True:
        user_query = input("\nEnter your question (or 'exit'): ")
        if user_query.lower() in ["exit", "quit"]:
            break
        result = agent.handle_query(user_query)
        print("\n=== Result ===")
        print(result)