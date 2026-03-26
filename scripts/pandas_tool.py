import pandas as pd
from .safe_executor import safe_execute

class PandasTool:
    def __init__(self, df):
        self.df = df

    def execute(self, code):
        """
        Executes Pandas code safely via safe_execute.
        Must assign output to 'result'.
        """
        # Clean the code
        lines = code.split("\n")
        clean_lines = [line for line in lines if line.strip().lower() not in ["pandas_tool", "visualization_tool"]]
        cleaned_code = "\n".join(clean_lines)

        # Run code in safe executor (separate process)
        result = safe_execute(cleaned_code, self.df, timeout=5)

        if "error" in result:
            return f"Pandas execution error: {result['error']}"

        # Return the computed result
        return result.get("result")