import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO

st.set_page_config(
    page_title="Universal AI Dashboard",
    page_icon="📊",
    layout="wide"
)

# ==========================================================
# TITLE
# ==========================================================

st.title("📊 Universal AI Dashboard Generator")
st.markdown(
    "Upload Excel, CSV, JSON, LOG, CEF or LEEF files and generate dashboards automatically."
)

# ==========================================================
# LOG PARSERS
# ==========================================================

def parse_cef_line(line):

    row = {}

    try:

        if "CEF:" in line:

            cef = line.split("CEF:")[1]

            for part in cef.split():

                if "=" in part:

                    k, v = part.split("=", 1)

                    row[k] = v

    except:
        pass

    return row


def parse_leef_line(line):

    row = {}

    try:

        if "LEEF:" in line:

            leef = line.split("LEEF:")[1]

            fields = leef.split("^")

            for item in fields:

                if "=" in item:

                    k, v = item.split("=", 1)

                    row[k] = v

    except:
        pass

    return row


def parse_json_line(line):

    try:

        start = line.find("{")

        if start >= 0:

            obj = json.loads(line[start:])

            return pd.json_normalize(obj).iloc[0].to_dict()

    except:
        pass

    return None


# ==========================================================
# UNIVERSAL LOG PARSER
# ==========================================================

def parse_log(uploaded_file):

    rows = []

    content = uploaded_file.read().decode(
        "utf-8",
        errors="ignore"
    )

    for line in content.splitlines():

        line = line.strip()

        if not line:
            continue

        if "CEF:" in line:

            row = parse_cef_line(line)

            if row:
                rows.append(row)

        elif "LEEF:" in line:

            row = parse_leef_line(line)

            if row:
                rows.append(row)

        elif "{" in line:

            row = parse_json_line(line)

            if row:
                rows.append(row)

    return pd.DataFrame(rows)


# ==========================================================
# FILE UPLOAD
# ==========================================================

uploaded_file = st.file_uploader(
    "Upload File",
    type=[
        "xlsx",
        "xls",
        "csv",
        "json",
        "log",
        "txt",
        "cef",
        "leef"
    ]
)

if uploaded_file is None:

    st.info("Upload a file to begin analysis.")

    st.stop()

# ==========================================================
# READ FILE
# ==========================================================

filename = uploaded_file.name.lower()

try:

    if filename.endswith(
        (".xlsx", ".xls")
    ):

        df = pd.read_excel(uploaded_file)

    elif filename.endswith(".csv"):

        df = pd.read_csv(
            uploaded_file,
            low_memory=False
        )

    elif filename.endswith(".json"):

        data = json.load(uploaded_file)

        if isinstance(data, list):

            df = pd.json_normalize(data)

        else:

            df = pd.json_normalize([data])

    else:

        df = parse_log(uploaded_file)

except Exception as e:

    st.error(f"Error reading file: {e}")

    st.stop()
# ==========================================================
# PERFORMANCE OPTIMIZATION FOR LARGE FILES
# ==========================================================

MAX_ROWS = 100000

try:

    total_rows = len(df)

    if total_rows > MAX_ROWS:

        st.warning(
            f"⚡ Large dataset detected ({total_rows:,} rows). "
            f"Using a sample of {MAX_ROWS:,} rows for faster dashboard generation."
        )

        df = df.sample(
            n=MAX_ROWS,
            random_state=42
        )

except:
    pass

# Reduce memory usage

for col in df.select_dtypes(include=["int64"]).columns:

    try:
        df[col] = pd.to_numeric(
            df[col],
            downcast="integer"
        )
    except:
        pass

for col in df.select_dtypes(include=["float64"]).columns:

    try:
        df[col] = pd.to_numeric(
            df[col],
            downcast="float"
        )
    except:
        pass

# Remove duplicate rows

try:

    before = len(df)

    df = df.drop_duplicates()

    after = len(df)

    if before != after:

        st.info(
            f"Removed {before-after:,} duplicate rows."
        )

except:
    pass

# Fill missing values

try:

    for col in df.columns:

        if df[col].dtype == "object":

            df[col] = df[col].fillna("Unknown")

        else:

            df[col] = df[col].fillna(0)

except:
    pass

st.success(
    f"✅ Dataset ready for analysis ({len(df):,} rows loaded)"
)
# ==========================================================
# CLEAN COLUMNS
# ==========================================================

df.columns = (
    df.columns
      .astype(str)
      .str.strip()
      .str.replace(" ", "_")
      .str.lower()
)

# ==========================================================
# AUTO DETECT TYPES
# ==========================================================

numeric_cols = list(
    df.select_dtypes(
        include=np.number
    ).columns
)

datetime_cols = []

for col in df.columns:

    try:

        converted = pd.to_datetime(
            df[col],
            errors="raise"
        )

        df[col] = converted

        datetime_cols.append(col)

    except:
        pass

categorical_cols = [
    c for c in df.columns
    if c not in numeric_cols
    and c not in datetime_cols
]

# ==========================================================
# KPI CARDS
# ==========================================================

st.subheader("📈 Dataset Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Rows",
    f"{len(df):,}"
)

c2.metric(
    "Columns",
    len(df.columns)
)

c3.metric(
    "Numeric Fields",
    len(numeric_cols)
)

c4.metric(
    "Categorical Fields",
    len(categorical_cols)
)

st.divider()
# ==========================================================
# DATA PREVIEW
# ==========================================================

st.subheader("📋 Data Preview")

st.dataframe(
    df.head(100),
    width="stretch"
)

st.divider()

# ==========================================================
# GLOBAL FILTERS
# ==========================================================

st.subheader("🎯 Interactive Filters")

filtered_df = df.copy()

filter_columns = st.multiselect(
    "Select Columns To Filter",
    df.columns.tolist()
)

for col in filter_columns:

    if col in numeric_cols:

        min_val = float(df[col].min())
        max_val = float(df[col].max())

        selected = st.slider(
            f"{col}",
            min_val,
            max_val,
            (min_val, max_val)
        )

        filtered_df = filtered_df[
            filtered_df[col].between(
                selected[0],
                selected[1]
            )
        ]

    else:

        values = st.multiselect(
            f"{col}",
            df[col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        if values:

            filtered_df = filtered_df[
                filtered_df[col]
                .astype(str)
                .isin(values)
            ]

st.divider()

# ==========================================================
# BAR CHARTS
# ==========================================================

st.subheader("📊 Category Analysis")

for col in categorical_cols[:3]:

    try:

        chart_data = (
            filtered_df[col]
            .astype(str)
            .value_counts()
            .head(15)
            .reset_index()
        )

        chart_data.columns = [
            col,
            "Count"
        ]

        fig = px.bar(
            chart_data,
            x=col,
            y="Count",
            title=f"{col} Distribution"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

    except:
        pass

st.divider()

# ==========================================================
# PIE CHARTS
# ==========================================================

st.subheader("🥧 Pie Charts")

for col in categorical_cols[:2]:

    try:

        pie_data = (
            filtered_df[col]
            .astype(str)
            .value_counts()
            .head(10)
            .reset_index()
        )

        pie_data.columns = [
            col,
            "Count"
        ]

        fig = px.pie(
            pie_data,
            names=col,
            values="Count",
            title=f"{col} Share"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

    except:
        pass

st.divider()

# ==========================================================
# HISTOGRAMS
# ==========================================================

st.subheader("📉 Numeric Distributions")

for col in numeric_cols[:5]:

    try:

        fig = px.histogram(
            filtered_df,
            x=col,
            title=f"{col} Distribution"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

    except:
        pass

st.divider()

# ==========================================================
# BOXPLOTS
# ==========================================================

st.subheader("📦 Outlier Detection")

for col in numeric_cols[:4]:

    try:

        fig = px.box(
            filtered_df,
            y=col,
            title=f"{col} Box Plot"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

    except:
        pass

st.divider()
# ==========================================================
# CORRELATION HEATMAP
# ==========================================================

if len(numeric_cols) >= 2 and len(numeric_cols) <= 15:

    st.subheader("🔥 Correlation Heatmap")

    try:

        corr = filtered_df[numeric_cols].corr(
            numeric_only=True
        )

        fig = px.imshow(
            corr,
            text_auto=True,
            aspect="auto",
            title="Correlation Matrix"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

    except:
        pass

st.divider()

# ==========================================================
# TIME SERIES ANALYSIS
# ==========================================================

if len(datetime_cols) > 0:

    st.subheader("📅 Time Series Analysis")

    date_col = datetime_cols[0]

    for num_col in numeric_cols[:3]:

        try:

            ts_df = (
                filtered_df
                .groupby(date_col)[num_col]
                .sum()
                .reset_index()
            )

            fig = px.line(
                ts_df,
                x=date_col,
                y=num_col,
                markers=True,
                title=f"{num_col} Trend Over Time"
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        except:
            pass

st.divider()

# ==========================================================
# SCATTER PLOTS
# ==========================================================

if len(numeric_cols) >= 2:

    st.subheader("🎯 Relationship Analysis")

    for i in range(
        min(2, len(numeric_cols)-1)
    ):

        try:

            fig = px.scatter(
                filtered_df,
                x=numeric_cols[i],
                y=numeric_cols[i+1],
                title=f"{numeric_cols[i]} vs {numeric_cols[i+1]}"
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        except:
            pass

st.divider()

# ==========================================================
# DATA QUALITY REPORT
# ==========================================================

st.subheader("🧹 Data Quality")

q1, q2, q3, q4 = st.columns(4)

q1.metric(
    "Missing Values",
    int(filtered_df.isnull().sum().sum())
)

q2.metric(
    "Duplicate Rows",
    int(filtered_df.duplicated().sum())
)

q3.metric(
    "Rows After Filter",
    len(filtered_df)
)

q4.metric(
    "Columns",
    len(filtered_df.columns)
)

st.divider()

# ==========================================================
# SUMMARY STATISTICS
# ==========================================================

if len(numeric_cols) > 0:

    st.subheader("📈 Statistical Summary")

    st.dataframe(
        filtered_df[numeric_cols]
        .describe(),
        width="stretch"
    )

st.divider()

# ==========================================================
# COLUMN EXPLORER
# ==========================================================

st.subheader("🔍 Column Explorer")

selected_col = st.selectbox(
    "Select a Column",
    filtered_df.columns
)

st.write(
    f"Unique Values: {filtered_df[selected_col].nunique()}"
)

st.dataframe(
    filtered_df[[selected_col]]
    .head(100),
    width="stretch"
)

st.divider()

# ==========================================================
# DOWNLOAD SECTION
# ==========================================================

st.subheader("📥 Export")

csv = filtered_df.to_csv(
    index=False
)

st.download_button(
    label="Download Filtered Data (CSV)",
    data=csv,
    file_name="dashboard_export.csv",
    mime="text/csv"
)

# ==========================================================
# AI GENERATED INSIGHTS
# ==========================================================

st.subheader("🤖 Quick Insights")

try:

    insights = []

    insights.append(
        f"Dataset contains {len(filtered_df):,} rows and {len(filtered_df.columns)} columns."
    )

    if len(numeric_cols) > 0:

        biggest_col = (
            filtered_df[numeric_cols]
            .mean()
            .idxmax()
        )

        insights.append(
            f"Highest average numeric metric: {biggest_col}"
        )

    if len(categorical_cols) > 0:

        top_category = (
            filtered_df[categorical_cols[0]]
            .astype(str)
            .value_counts()
            .idxmax()
        )

        insights.append(
            f"Most frequent value in {categorical_cols[0]}: {top_category}"
        )

    for insight in insights:

        st.success(insight)

except:
    pass

st.divider()

# ==========================================================
# FOOTER
# ==========================================================

st.markdown("---")
st.markdown(
    """
    ### 🚀 Universal AI Dashboard Generator

    Supported Files:
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    - JSON (.json)
    - LOG (.log)
    - CEF (.cef)
    - LEEF (.leef)

    Features:
    - Auto Data Detection
    - Dynamic KPI Cards
    - Bar Charts
    - Pie Charts
    - Histograms
    - Scatter Plots
    - Correlation Heatmaps
    - Time Series Analysis
    - Data Quality Checks
    - Export Reports
    """
)
