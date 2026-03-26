# import multiprocessing
# import pandas as pd
# import plotly.express as px


# def run_code(queue, code, df):
#     # Cast numeric-looking columns to proper dtype so sum() works correctly
#     for col in df.columns:
#         if df[col].dtype == object:
#             try:
#                 df[col] = pd.to_numeric(df[col])
#             except (ValueError, TypeError):
#                 pass

#     local_vars = {
#         "df": df,
#         "pd": pd,
#         "px": px,
#         "result": None
#     }
#     safe_builtins = {
#         "len": len,
#         "sum": sum,
#         "min": min,
#         "max": max,
#         "range": range,
#         "str": str,
#         "int": int,
#         "float": float,
#         "print": print,
#         "enumerate": enumerate,
#         "zip": zip,
#         "list": list,
#         "dict": dict,
#         "sorted": sorted,
#         "round": round,
#     }

#     try:
#         exec(code, {"__builtins__": safe_builtins}, local_vars)
#         result_obj = local_vars.get("result")

#         validation = validate_result(result_obj)

#         if hasattr(result_obj, "to_json"):
#             # Serialize figure to plain JSON — Plotly encodes numeric arrays as
#             # base64 binary blobs ("bdata") which Plotly.js may misread.
#             # We decode them to plain Python lists before serializing.
#             import base64, struct, numpy as np

#             def sanitize(obj):
#                 if isinstance(obj, np.ndarray):
#                     return obj.tolist()
#                 if isinstance(obj, np.integer):
#                     return int(obj)
#                 if isinstance(obj, np.floating):
#                     return float(obj)
#                 if isinstance(obj, dict):
#                     if "bdata" in obj and "dtype" in obj:
#                         dtype_map = {"f8": ("d", 8), "f4": ("f", 4),
#                                      "i4": ("i", 4), "i2": ("h", 2)}
#                         fmt, size = dtype_map.get(obj["dtype"], ("d", 8))
#                         raw = base64.b64decode(obj["bdata"])
#                         n = len(raw) // size
#                         return list(struct.unpack(f"<{n}{fmt}", raw))
#                     return {k: sanitize(v) for k, v in obj.items()}
#                 if isinstance(obj, (list, tuple)):
#                     return [sanitize(i) for i in obj]
#                 return obj

#             import json as _json
#             fig_dict = sanitize(result_obj.to_dict())
#             json_str = _json.dumps(fig_dict)
#             queue.put({
#                 "type": "plotly",
#                 "data": json_str,
#                 "validation": validation
#             })

#         elif isinstance(result_obj, pd.DataFrame):
#             # Serialize DataFrame to dict to survive multiprocessing pickling
#             queue.put({
#                 "type": "data",
#                 "result": result_obj.to_dict(orient="split"),
#                 "result_type": "dataframe",
#                 "validation": validation
#             })

#         elif isinstance(result_obj, pd.Series):
#             queue.put({
#                 "type": "data",
#                 "result": result_obj.reset_index().to_dict(orient="split"),
#                 "result_type": "series",
#                 "validation": validation
#             })

#         else:
#             queue.put({
#                 "type": "data",
#                 "result": result_obj,
#                 "result_type": "scalar",
#                 "validation": validation
#             })

#     except Exception as e:
#         queue.put({"error": str(e)})


# def validate_result(result):
#     if result is None:
#         return {"valid": False, "reason": "Result is None"}
#     if hasattr(result, "to_json"):
#         return {"valid": True, "reason": "Valid Plotly figure"}
#     if isinstance(result, pd.DataFrame):
#         if result.empty:
#             return {"valid": False, "reason": "DataFrame is empty"}
#         if result.columns.duplicated().any():
#             return {"valid": False, "reason": "Duplicate columns"}
#         return {"valid": True, "reason": "Valid DataFrame"}
#     if isinstance(result, pd.Series):
#         if result.empty:
#             return {"valid": False, "reason": "Series is empty"}
#         return {"valid": True, "reason": "Valid Series"}
#     if isinstance(result, (int, float, str)):
#         return {"valid": True, "reason": "Scalar result"}
#     return {"valid": False, "reason": f"Unexpected type: {type(result)}"}


# def safe_execute(code, df, timeout=10):
#     queue = multiprocessing.Queue()
#     process = multiprocessing.Process(target=run_code, args=(queue, code, df))
#     process.start()
#     process.join(timeout)

#     if process.is_alive():
#         process.terminate()
#         process.join()
#         return {"error": "Execution timed out"}

#     if not queue.empty():
#         output = queue.get()

#         if "error" in output:
#             return output

#         if "validation" in output and not output["validation"]["valid"]:
#             return {
#                 "error": f"Validation failed: {output['validation']['reason']}",
#                 **output
#             }

#         return output

#     return {"error": "No output returned"}




# import multiprocessing
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objs as go
# import numpy as np


# # =========================
# # VALIDATION
# # =========================
# def validate_result(result):
#     if result is None:
#         return {"valid": False, "reason": "Result is None"}

#     if isinstance(result, pd.DataFrame):
#         if result.empty:
#             return {"valid": False, "reason": "Empty DataFrame"}
#         return {"valid": True, "reason": "DataFrame OK"}

#     if isinstance(result, pd.Series):
#         if result.empty:
#             return {"valid": False, "reason": "Empty Series"}
#         return {"valid": True, "reason": "Series OK"}

#     return {"valid": True, "reason": "Object OK"}


# # =========================
# # CLEAN SERIALIZER (IMPORTANT)
# # =========================
# def deep_clean(obj):
#     if isinstance(obj, np.ndarray):
#         return obj.tolist()
#     if isinstance(obj, (np.integer, np.floating)):
#         return obj.item()
#     if isinstance(obj, dict):
#         return {k: deep_clean(v) for k, v in obj.items()}
#     if isinstance(obj, list):
#         return [deep_clean(i) for i in obj]
#     return obj


# # =========================
# # WORKER
# # =========================
# def run_code(queue, code, df):

#     # -------------------------
#     # FIX 1: STRICT numeric conversion
#     # -------------------------
#     for col in df.columns:
#         try:
#             df[col] = pd.to_numeric(df[col])
#         except:
#             pass

#     # -------------------------
#     # FIX 2: datetime conversion
#     # -------------------------
#     for col in df.columns:
#         if "date" in col.lower() or "time" in col.lower():
#             df[col] = pd.to_datetime(df[col], errors="coerce")

#     if "Order Date" in df.columns:
#         df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

#     # -------------------------
#     # CONTEXT
#     # -------------------------
#     local_vars = {
#         "df": df,
#         "pd": pd,
#         "px": px,
#         "np": np,
#         "result": None
#     }

#     safe_builtins = {
#         "len": len, "sum": sum, "min": min, "max": max,
#         "range": range, "str": str, "int": int, "float": float,
#         "print": print, "enumerate": enumerate, "zip": zip,
#         "list": list, "dict": dict, "sorted": sorted, "round": round,
#     }

#     try:
#         exec(code, {"__builtins__": safe_builtins}, local_vars)

#         result_obj = local_vars.get("result")
#         validation = validate_result(result_obj)

#         # =========================
#         # DATAFRAME
#         # =========================
#         if isinstance(result_obj, pd.DataFrame):
#             queue.put({
#                 "result": result_obj.to_dict(orient="records"),
#                 "type": "dataframe",
#                 "validation": validation
#             })
#             return

#         # =========================
#         # SERIES (FIX INDEX ISSUE HERE)
#         # =========================
#         if isinstance(result_obj, pd.Series):
#             df_series = result_obj.reset_index()
#             df_series.columns = ["index", "value"]

#             queue.put({
#                 "result": df_series.to_dict(orient="records"),
#                 "type": "series",
#                 "validation": validation
#             })
#             return

#         # =========================
#         # PLOTLY FIX (MAIN FIX)
#         # =========================
#         if isinstance(result_obj, go.Figure):

#             fig_json = result_obj.to_plotly_json()

#             # 🔥 FULL CLEAN (THIS FIXES YOUR CRASH)
#             fig_json = deep_clean(fig_json)

#             queue.put({
#                 "result": fig_json,
#                 "type": "plotly",
#                 "validation": validation
#             })
#             return

#         # =========================
#         # FALLBACK
#         # =========================
#         queue.put({
#             "result": result_obj,
#             "type": "scalar",
#             "validation": validation
#         })

#     except Exception as e:
#         queue.put({"error": str(e)})


# # =========================
# # EXECUTOR
# # =========================
# def safe_execute(code, df, timeout=30):

#     queue = multiprocessing.Queue()
#     process = multiprocessing.Process(target=run_code, args=(queue, code, df))

#     process.start()
#     process.join(timeout)

#     if process.is_alive():
#         process.terminate()
#         process.join()
#         return {"error": "Execution timed out"}

#     if queue.empty():
#         return {"error": "No output returned"}

#     output = queue.get()
#     print("=== RAW OUTPUT ===", output)
#     return output




import multiprocessing
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import numpy as np


# =========================
# VALIDATION
# =========================
def validate_result(result):
    if result is None:
        return {"valid": False, "reason": "Result is None"}

    if isinstance(result, pd.DataFrame):
        if result.empty:
            return {"valid": False, "reason": "Empty DataFrame"}
        return {"valid": True, "reason": "DataFrame OK"}

    if isinstance(result, pd.Series):
        if result.empty:
            return {"valid": False, "reason": "Empty Series"}
        return {"valid": True, "reason": "Series OK"}

    return {"valid": True, "reason": "Object OK"}


# =========================
# CLEAN SERIALIZER
# =========================
import base64
import struct

def deep_clean(obj):
    # numpy arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()

    # 🔥 FIX: decode Plotly binary arrays
    if isinstance(obj, dict):
        if "bdata" in obj and "dtype" in obj:
            dtype_map = {
                "f8": ("d", 8),
                "f4": ("f", 4),
                "i4": ("i", 4),
                "i2": ("h", 2),
            }

            fmt, size = dtype_map.get(obj["dtype"], ("d", 8))

            raw = base64.b64decode(obj["bdata"])
            n = len(raw) // size

            return list(struct.unpack(f"<{n}{fmt}", raw))

        return {k: deep_clean(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [deep_clean(i) for i in obj]

    return obj

def fix_common_errors(code: str) -> str:

    # Fix missing closing bracket in df[...] patterns
    if "df[df[" in code and "].copy()" not in code:
        code = code.replace(").copy()", "]) .copy()")  # quick patch

    # Fix unclosed brackets count (basic)
    if code.count("[") > code.count("]"):
        code += "]" * (code.count("[") - code.count("]"))

    # Fix missing parenthesis
    if code.count("(") > code.count(")"):
        code += ")" * (code.count("(") - code.count(")"))

    return code
# =========================
# 🔥 FIXED DATA CLEANING FUNCTION
# =========================
def clean_dataframe(df):

    df = df.copy()

    # remove whitespace in column names (VERY IMPORTANT)
    df.columns = [str(c).strip() for c in df.columns]

    # convert numeric safely
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")

    # force convert object numeric columns properly
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # datetime handling
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

    return df


# =========================
# WORKER
# =========================
def run_code(queue, code, df):

    df = clean_dataframe(df)

    local_vars = {
        "df": df,
        "pd": pd,
        "px": px,
        "np": np,
        "result": None
    }

    safe_builtins = {
        "len": len, "sum": sum, "min": min, "max": max,
        "range": range, "str": str, "int": int, "float": float,
        "print": print, "enumerate": enumerate, "zip": zip,
        "list": list, "dict": dict, "sorted": sorted, "round": round,
    }

    try:
        code = fix_common_errors(code)

        exec(code, {"__builtins__": safe_builtins}, local_vars)

        result_obj = local_vars.get("result")
        validation = validate_result(result_obj)

        # =========================
        # DATAFRAME FIX
        # =========================
        if isinstance(result_obj, pd.DataFrame):
            result_obj = result_obj.copy()

            # force numeric cleanup again (IMPORTANT FOR PLOTS)
            for col in result_obj.columns:
                result_obj[col] = pd.to_numeric(result_obj[col], errors="ignore")

            queue.put({
                "result": result_obj.to_dict(orient="records"),
                "type": "dataframe",
                "validation": validation
            })
            return

        # =========================
        # SERIES FIX (THIS FIXES YOUR INDEX/Y ISSUE)
        # =========================
        if isinstance(result_obj, pd.Series):

            result_obj = pd.to_numeric(result_obj, errors="coerce").dropna()

            df_series = result_obj.reset_index()
            df_series.columns = ["x", "y"]

            queue.put({
                "result": df_series.to_dict(orient="records"),
                "type": "series",
                "validation": validation
            })
            return

        # =========================
        # PLOTLY FIX (IMPORTANT)
        # =========================
        if isinstance(result_obj, go.Figure):

            fig_json = result_obj.to_plotly_json()
            fig_json = deep_clean(fig_json)

            queue.put({
                "result": fig_json,
                "type": "plotly",
                "validation": validation
            })
            return

        # =========================
        # FALLBACK
        # =========================
        queue.put({
            "result": result_obj,
            "type": "scalar",
            "validation": validation
        })

    except Exception as e:
        queue.put({"error": str(e)})


# =========================
# EXECUTOR
# =========================
def safe_execute(code, df, timeout=30):

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_code, args=(queue, code, df))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        return {"error": "Execution timed out"}

    if queue.empty():
        return {"error": "No output returned"}

    output = queue.get()
    print("=== RAW OUTPUT ===", output)
    return output