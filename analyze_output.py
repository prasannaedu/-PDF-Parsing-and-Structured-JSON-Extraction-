import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

# Load JSON
try:
    with open("output_enriched.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: output_enriched.json not found. Please run pdf_to_json.py first.")
    exit(1)

tables = []
for page in data["pages"]:
    for block in page["content"]:
        if block["type"] == "table":
            tables.append({
                "table_data": block.get("table_data", []),
                "section": block.get("section", ""),
                "page": page["page_number"]
            })

print(f"Total tables extracted: {len(tables)}\n")

# Debug: Print table info to identify issues
for t in tables:
    section = t.get("section", "None")
    first_row = t["table_data"][0] if t["table_data"] and len(t["table_data"]) > 0 else "No data"
    print(f"Page {t['page']}: Section '{section}' - First Row: {first_row}")

# Find performance tables
performance_tables = []
for t in tables:
    table_data = t["table_data"]
    section = str(t.get("section", ""))  # Ensure string
    first_row = str(table_data[0]) if table_data and len(table_data) > 0 else ""
    if ("Performance Data" in section or 
        "Scheme Performance" in first_row or 
        "PTP" in first_row):
        performance_tables.append(t)

# Find holdings tables
holdings_tables = []
for t in tables:
    table_data = t["table_data"]
    section = str(t.get("section", ""))  # Ensure string
    first_row = str(table_data[0]) if table_data and len(table_data) > 0 else ""
    if ("Holdings" in section or 
        "Portfolio as on" in first_row or 
        (table_data and any("%" in str(cell) for row in table_data for cell in row) and len(table_data) > 1)):
        holdings_tables.append(t)

# --- Process Holdings Data (Horizontal Bar Chart for Top Holdings) ---
if holdings_tables:
    holdings_data = []
    for table in holdings_tables:
        table_data = table["table_data"]
        for row in table_data:
            if len(row) >= 2 and '%' in str(row[-1]):  # Look for % in last column for safety
                name = row[0].strip() if row[0] else "Unknown"
                percent_str = re.sub(r'[^\d.-]', '', str(row[-1]))
                try:
                    percent = float(percent_str)
                    if percent > 0:  # Skip negative or zero
                        holdings_data.append((name, percent))
                except ValueError:
                    continue
    
    if holdings_data:
        df = pd.DataFrame(holdings_data, columns=['Company', 'Percentage'])
        df = df.drop_duplicates().sort_values('Percentage', ascending=False).head(10)
        if not df.empty:
            plt.figure(figsize=(10, 6))
            colors = plt.cm.Set3(np.linspace(0, 1, len(df)))
            bars = plt.barh(df['Company'], df['Percentage'], color=colors)
            plt.xlabel('% to Net Assets')
            plt.title('Top Holdings')
            plt.gca().invert_yaxis()
            for bar, value in zip(bars, df['Percentage']):
                plt.text(value + 0.1, bar.get_y() + bar.get_height()/2, f'{value:.2f}%', 
                         va='center', fontweight='bold')
            plt.tight_layout()
            plt.savefig('top_holdings.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("✅ Saved chart: top_holdings.png")

# --- Process Performance Data ---
if performance_tables:
    table_data = performance_tables[0]["table_data"] if performance_tables else []
    
    perf_data = []
    for row in table_data:
        if row and any('%' in str(cell) for cell in row if cell):
            perf_data.append([str(cell).strip() for cell in row if cell])
    
    if perf_data:
        schemes = []
        returns = []
        for row in perf_data:
            if len(row) > 1 and row[0] and '%' in row[1]:
                scheme = row[0]
                val_str = re.sub(r'[^\d.-]', '', row[1])
                try:
                    val = float(val_str)
                    schemes.append(scheme)
                    returns.append(val)
                except ValueError:
                    continue
        
        if schemes and returns:
            plt.figure(figsize=(12, 8))
            colors = plt.cm.viridis(np.linspace(0, 1, len(schemes)))
            bars = plt.bar(schemes, returns, color=colors)
            plt.ylabel('1-Year Return (%)')
            plt.title('Scheme Performance - 1 Year Returns')
            plt.xticks(rotation=45, ha='right')
            for bar, ret in zip(bars, returns):
                plt.text(bar.get_x() + bar.get_width()/2, max(ret, 0) + 0.1 if ret > 0 else ret - 0.5, 
                         f'{ret}%', ha='center', va='bottom' if ret > 0 else 'top', fontweight='bold')
            plt.tight_layout()
            plt.savefig('performance.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("✅ Saved chart: performance.png")

# --- Macro-Economic Indicators Line Chart (e.g., Inflation Trends) ---
macro_tables = []
for t in tables:
    table_data = t["table_data"]
    section = str(t.get("section", "")).lower()  # Ensure string and convert to lowercase
    first_row = str(table_data[0]) if table_data and len(table_data) > 0 else ""
    if ("macro" in section or "macro-economic indicators" in first_row.lower()) and table_data:
        macro_tables.append(t)

if macro_tables:
    table_data = macro_tables[0]["table_data"]
    df_macro = pd.DataFrame(table_data[1:], columns=table_data[0] if table_data[0] else [])
    df_macro.set_index(df_macro.columns[0], inplace=True)
    df_macro = df_macro.apply(pd.to_numeric, errors='coerce')
    
    if 'CPI (%YoY)' in df_macro.index and 'WPI (%YoY)' in df_macro.index:
        months = df_macro.columns.tolist()
        plt.figure(figsize=(10, 6))
        plt.plot(months, df_macro.loc['CPI (%YoY)'], marker='o', label='CPI (%YoY)')
        plt.plot(months, df_macro.loc['WPI (%YoY)'], marker='s', label='WPI (%YoY)')
        plt.title('Inflation Trends')
        plt.xlabel('Month')
        plt.ylabel('% YoY')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('inflation_trends.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ Saved chart: inflation_trends.png")

# --- Nifty EPS Bar Chart ---
nifty_table = [t for t in tables if "Nifty EPS" in str(t["table_data"][0]) if t["table_data"]]
if not nifty_table:  # Fallback to hardcoded data if not in tables
    nifty_years = ['FY02', 'FY03', 'FY04', 'FY05', 'FY06', 'FY07', 'FY08', 'FY09', 'FY10', 
                   'FY11', 'FY12', 'FY13', 'FY14', 'FY15', 'FY16', 'FY17', 'FY18', 'FY19', 
                   'FY20', 'FY21', 'FY22', 'FY23', 'FY24', 'FY25E', 'FY26E']
    nifty_eps = [78, 92, 131, 169, 184, 236, 281, 251, 247, 315, 348, 369, 405, 416, 397, 
                 427, 451, 483, 478, 542, 728, 807, 987, 1110, 1268]
else:
    table_data = nifty_table[0]["table_data"]
    nifty_years = table_data[0][1:] if len(table_data) > 1 and table_data[0] else []
    nifty_eps = [float(re.sub(r'[^\d.-]', '', str(cell))) for row in table_data[1:] for cell in row if re.match(r'^\d+\.?\d*$', str(cell))]
    if len(nifty_years) != len(nifty_eps):
        nifty_years = [f'FY{i:02d}' for i in range(len(nifty_eps))]  # Fallback numbering

if nifty_years and nifty_eps:
    plt.figure(figsize=(12, 6))
    plt.bar(nifty_years, nifty_eps, color='blue')
    plt.title('Nifty EPS Historical Trend')
    plt.xlabel('Fiscal Year')
    plt.ylabel('EPS')
    plt.xticks(rotation=90)
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig('nifty_eps.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved chart: nifty_eps.png")

# --- Debt Spreads Bar Chart ---
spreads_tables = [t for t in tables if "Spreads" in str(t["table_data"][0]) if t["table_data"]]
if spreads_tables:
    table_data = spreads_tables[0]["table_data"]
    df_spreads = pd.DataFrame(table_data[1:], columns=table_data[0])
    df_spreads.set_index(df_spreads.columns[0], inplace=True)
    df_spreads = df_spreads.apply(pd.to_numeric, errors='coerce')
    
    maturities = df_spreads.columns
    dates = df_spreads.index
    plt.figure(figsize=(10, 6))
    width = 0.35
    x = np.arange(len(maturities))
    for i, date in enumerate(dates):
        heights = df_spreads.loc[date].values  # Get all values for the date as a numpy array
        if len(heights) == len(maturities):  # Ensure alignment
            plt.bar(x + i * width, heights, width, label=date)
    plt.xlabel('Maturity Period')
    plt.ylabel('Spread (bps)')
    plt.title('Debt Spreads (AAA)')
    plt.xticks(x + width/2, maturities)
    plt.legend()
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig('debt_spreads.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved chart: debt_spreads.png")

print("\n📊 Visualization complete!")