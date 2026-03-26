# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns

# class VisualizationTool:
#     def __init__(self, df):
#         self.df = df

#     def execute(self, code):
#         """
#         Execute user-generated plotting code safely.
#         - Code can use df, pandas, matplotlib, seaborn
#         - Shows plots with plt.show()
#         - Returns the 'result' variable if assigned
#         """
#         local_vars = {
#             "df": self.df,
#             "pd": pd,
#             "plt": plt,
#             "sns": sns,
#             "result": None,
#             "len": len,
#             "sum": sum,
#             "min": min,
#             "max": max,
#             "sorted": sorted,
#             "range": range
#         }

#         try:
#             # Remove any lines with tool names
#             lines = code.split("\n")
#             clean_lines = [line for line in lines if line.strip().lower() not in ["pandas_tool", "visualization_tool"]]
#             cleaned_code = "\n".join(clean_lines)

#             safe_builtins = {"len": len, "sum": sum, "min": min, "max": max, "sorted": sorted, "range": range}

#             # Execute the code
#             exec(cleaned_code, {"__builtins__": safe_builtins}, local_vars)

#             # Show plot
#             plt.show()

#             # Return result if defined
#             return local_vars.get("result", "✅ Visualization generated!")

#         except Exception as e:
#             return f"Visualization execution error: {str(e)}"

import matplotlib
matplotlib.use("Agg")  # must be set before pyplot
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from .safe_executor import safe_execute

class VisualizationTool:
    def __init__(self, df):
        self.df = df

    def execute(self, code):
        cleaned_code = "\n".join([
            line for line in code.split("\n")
            if line.strip().lower() not in ["pandas_tool", "visualization_tool"]
        ])

        result = safe_execute(cleaned_code, self.df, timeout=5)

        if "error" in result:
            return f"Visualization execution error: {result['error']}"

        return result