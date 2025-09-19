#!/usr/bin/env python
import json
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, KeepInFrame
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os

# ----------- Load JSON -----------
with open("output_enriched.json", "r", encoding="utf-8") as f:
    data = json.load(f)

metadata = data.get("metadata", {})
sections = data.get("sections", {})

# ----------- Styles -----------
styles = getSampleStyleSheet()
title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20, alignment=1, spaceAfter=20)
cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)

# ----------- Helpers -----------
def to_dataframe(tbl_obj):
    """Convert section table object to pandas DataFrame."""
    if not tbl_obj:
        return None
    # tbl_obj is a dict {'page':..., 'table_data': ..., 'section_name': ...}
    table = tbl_obj.get("table_data")
    if table and len(table) > 1:
        return pd.DataFrame(table[1:], columns=table[0])
    return None

def wrap_table_data(df):
    """Return table data wrapped with Paragraphs for reportlab."""
    wrapped_data = []
    header = [Paragraph(str(c), cell_style) for c in df.columns]
    wrapped_data.append(header)
    for _, row in df.iterrows():
        wrapped_row = [Paragraph(str(val), cell_style) for val in row]
        wrapped_data.append(wrapped_row)
    return wrapped_data

PAGE_WIDTH = A4[0] - 100
def get_col_widths(df):
    return [PAGE_WIDTH / max(1, len(df.columns))] * len(df.columns)


# ----------- Extract Sections (pick first relevant table) -----------
top_holdings = None
sector_allocation = None
debt_allocation = None

if "portfolio" in sections and sections["portfolio"]:
    # choose the table with highest chance of being holdings (first one)
    top_holdings = to_dataframe(sections["portfolio"][0])
if "allocation" in sections and sections["allocation"]:
    sector_allocation = to_dataframe(sections["allocation"][0])
if "debt_portfolio" in sections and sections["debt_portfolio"]:
    debt_allocation = to_dataframe(sections["debt_portfolio"][0])

performance_tables = sections.get("scheme_performance", [])
risk_tables = sections.get("risk", [])
macro_tables = sections.get("macro", [])

# ----------- Fallback: Fund Name -----------
if not metadata.get("fund_name") or metadata["fund_name"].lower() in ["n/a", ""]:
    if performance_tables:
        df_tmp = to_dataframe(performance_tables[0])
        if df_tmp is not None and not df_tmp.empty:
            metadata["fund_name"] = str(df_tmp.iloc[0, 0])

# ----------- Utility: robust percent parsing -----------
def extract_numeric_series(series):
    # take series of strings, return numeric values where possible
    s = series.astype(str)
    s = s.str.replace("%", "", regex=False)
    s = s.str.replace(",", "", regex=False)
    # extract first number in string
    s = s.str.extract(r'([-+]?\d*\.\d+|\d+)', expand=False)
    return pd.to_numeric(s, errors="coerce")


# ----------- Charts -----------

# --- Top Holdings chart (horizontal bar)
if top_holdings is not None and not top_holdings.empty:
    # find candidate percent column
    percent_cols = [c for c in top_holdings.columns if "%" in str(c).lower() or "weight" in str(c).lower() or "net" in str(c).lower()]
    if not percent_cols:
        # try last column as fallback
        percent_cols = [top_holdings.columns[-1]]
    percent_col = percent_cols[0]
    try:
        df = top_holdings.copy()
        df[percent_col] = extract_numeric_series(df[percent_col])
        df = df.dropna(subset=[percent_col]).head(10)
        if not df.empty:
            plt.figure(figsize=(8, 5))
            # label column: first column in table (company name usually)
            label_col = df.columns[0]
            plt.barh(df[label_col].astype(str), df[percent_col])
            plt.xlabel(percent_col)
            plt.title("Top 10 Holdings")
            plt.gca().invert_yaxis()
            plt.tight_layout()
            plt.savefig("top_holdings.png")
            plt.close()
            print("Saved top_holdings.png")
    except Exception as e:
        print("Could not create top_holdings chart:", e)

# --- Sector Allocation (pie)
if sector_allocation is not None and not sector_allocation.empty:
    percent_cols = [c for c in sector_allocation.columns if "%" in str(c).lower() or "nav" in str(c).lower() or "weight" in str(c).lower()]
    if percent_cols:
        percent_col = percent_cols[0]
        try:
            df = sector_allocation.copy()
            df[percent_col] = extract_numeric_series(df[percent_col])
            df = df.dropna(subset=[percent_col])
            if not df.empty:
                plt.figure(figsize=(6, 6))
                labels = df[df.columns[0]].astype(str)
                plt.pie(df[percent_col], labels=labels, autopct="%1.1f%%")
                plt.title("Sector Allocation")
                plt.tight_layout()
                plt.savefig("sector_allocation.png")
                plt.close()
                print("Saved sector_allocation.png")
        except Exception as e:
            print("Could not create sector_allocation chart:", e)

# --- Debt Allocation (pie fallback)
if debt_allocation is not None and not debt_allocation.empty:
    try:
        percent_col = debt_allocation.columns[-1]
        df = debt_allocation.copy()
        df[percent_col] = extract_numeric_series(df[percent_col])
        df = df.dropna(subset=[percent_col])
        if not df.empty:
            plt.figure(figsize=(6, 6))
            labels = df[df.columns[0]].astype(str)
            plt.pie(df[percent_col], labels=labels, autopct="%1.1f%%")
            plt.title("Debt / Credit Rating Allocation")
            plt.tight_layout()
            plt.savefig("debt_allocation.png")
            plt.close()
            print("Saved debt_allocation.png")
    except Exception as e:
        print("Could not create debt_allocation chart:", e)

# --- Performance chart (bar for 1 year returns)
if performance_tables:
    perf_tbl = performance_tables[0]
    df = to_dataframe(perf_tbl)
    if df is not None:
        # assume first column is scheme, look for column with % values for 1 year
        percent_cols = [c for c in df.columns if any("%" in str(val) for val in df[c])]
        if percent_cols:
            # take the first % column as 1 year (assuming it's Last 1 year)
            one_yr_col = percent_cols[0]
            df[one_yr_col] = extract_numeric_series(df[one_yr_col])
            df = df.dropna(subset=[one_yr_col])
            if not df.empty:
                plt.figure(figsize=(8, 5))
                label_col = df.columns[0]
                plt.bar(df[label_col].astype(str), df[one_yr_col])
                plt.ylabel('1 Year Return (%)')
                plt.title("1 Year Performance")
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig("performance.png")
                plt.close()
                print("Saved performance.png")

# ----------- PDF Report building -----------
doc = SimpleDocTemplate("final_report.pdf", pagesize=A4)
story = []

# Cover page
story.append(Paragraph(metadata.get("fund_name", "Mutual Fund Factsheet Report"), title_style))
story.append(Spacer(1, 12))

snapshot_data = [
    ["Fund Name", metadata.get("fund_name", "N/A")],
    ["AUM", metadata.get("aum", "N/A")],
    ["Benchmark", metadata.get("benchmark", "N/A")],
    ["Additional Benchmark", metadata.get("additional_benchmark", "N/A")],
    ["Fund Manager", metadata.get("fund_manager", "N/A")],
    ["Launch Date", metadata.get("launch_date", "N/A")]
]
snapshot_wrapped = [[Paragraph(str(x), cell_style), Paragraph(str(y), cell_style)] for x, y in snapshot_data]
snapshot_table = Table(snapshot_wrapped, colWidths=[150, 300])
snapshot_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
]))
story.append(snapshot_table)
story.append(PageBreak())

# Charts
if os.path.exists("top_holdings.png"):
    story.append(Paragraph("Top Holdings", styles["Heading2"]))
    story.append(Image("top_holdings.png", width=400, height=250))
    story.append(Spacer(1, 20))

if os.path.exists("sector_allocation.png"):
    story.append(Paragraph("Sector Allocation", styles["Heading2"]))
    story.append(Image("sector_allocation.png", width=400, height=250))
    story.append(Spacer(1, 20))

if os.path.exists("debt_allocation.png"):
    story.append(Paragraph("Debt / Credit Rating Allocation", styles["Heading2"]))
    story.append(Image("debt_allocation.png", width=400, height=250))
    story.append(Spacer(1, 20))

if os.path.exists("performance.png"):
    story.append(Paragraph("Performance", styles["Heading2"]))
    story.append(Image("performance.png", width=400, height=250))
    story.append(Spacer(1, 20))

# Performance tables
if performance_tables:
    story.append(Paragraph("Scheme Performance", styles["Heading2"]))
    for tbl in performance_tables:
        df = to_dataframe(tbl)
        if df is None:
            continue
        try:
            table_data = wrap_table_data(df)
            col_widths = get_col_widths(df)
            perf_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            perf_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            story.append(KeepInFrame(500, 400, [perf_table], hAlign="CENTER"))
            story.append(Spacer(1, 12))
        except Exception as e:
            print("Could not render a performance table:", e)

# Risk tables
if risk_tables:
    story.append(Paragraph("Risk Metrics", styles["Heading2"]))
    for tbl in risk_tables:
        df = to_dataframe(tbl)
        if df is None:
            continue
        try:
            table_data = wrap_table_data(df)
            col_widths = get_col_widths(df)
            risk_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#660000")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            story.append(KeepInFrame(500, 300, [risk_table], hAlign="CENTER"))
            story.append(Spacer(1, 12))
        except Exception as e:
            print("Could not render a risk table:", e)

# Macro / Economic tables
if macro_tables:
    story.append(Paragraph("Macro / Economic Indicators", styles["Heading2"]))
    for tbl in macro_tables:
        df = to_dataframe(tbl)
        if df is None:
            continue
        try:
            table_data = wrap_table_data(df)
            col_widths = get_col_widths(df)
            macro_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            macro_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003300")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]))
            story.append(KeepInFrame(500, 300, [macro_table], hAlign="CENTER"))
            story.append(Spacer(1, 12))
        except Exception as e:
            print("Could not render a macro table:", e)

# Disclaimer
story.append(Paragraph(
    "Mutual Fund Investments are subject to market risks. Read all scheme related documents carefully.",
    styles["Normal"]
))

doc.build(story)
print("✅ Final PDF generated successfully: final_report.pdf")