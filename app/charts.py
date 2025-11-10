import pandas as pd
import plotly.express as px

def guess_and_plot(df: pd.DataFrame):
    """
    Heuristic:
    - If two columns: 1 cat + 1 numeric -> bar
    - If first column looks like date -> line by date
    - Else: just return None (table only)
    """
    if df is None or df.empty:
        return None
    if df.shape[1] == 2:
        a,b = df.columns
        if pd.api.types.is_datetime64_any_dtype(df[a]) and pd.api.types.is_numeric_dtype(df[b]):
            fig = px.line(df.sort_values(a), x=a, y=b)
            return fig
        if pd.api.types.is_numeric_dtype(df[a]) and pd.api.types.is_datetime64_any_dtype(df[b]):
            fig = px.line(df.sort_values(b), x=b, y=a)
            return fig
        # make a bar if one numeric and one non-numeric
        if pd.api.types.is_numeric_dtype(df[b]) and not pd.api.types.is_numeric_dtype(df[a]):
            fig = px.bar(df, x=a, y=b)
            return fig
        if pd.api.types.is_numeric_dtype(df[a]) and not pd.api.types.is_numeric_dtype(df[b]):
            fig = px.bar(df, x=b, y=a)
            return fig

    # If a 'month' or 'date' column exists, prefer line
    for col in df.columns:
        if "month" in col.lower() or "date" in col.lower() or "timestamp" in col.lower():
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                # choose a numeric y
                num_cols = [c for c in df.columns if c != col and pd.api.types.is_numeric_dtype(df[c])]
                if num_cols:
                    fig = px.line(df.sort_values(col), x=col, y=num_cols[0])
                    return fig
    return None
