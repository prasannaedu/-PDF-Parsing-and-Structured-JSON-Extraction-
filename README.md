# PDF Parser and Report Generator

## Project Overview
This project extracts structured data from a **Mutual Fund PDF Factsheet** and generates:
1. A **structured JSON file** (`output_enriched.json`) containing metadata, tables, and charts.
2. A **polished PDF Report** (`final_report.pdf`) with a cover page, tables, and visualizations.

The solution demonstrates:
- PDF parsing and structured data extraction.
- Organizing data into a hierarchical JSON format (pages, sections, tables, charts).
- Generating analytical charts (e.g., Top Holdings, Performance, Nifty EPS, Debt Spreads).
- Exporting a professional-looking PDF report.

This project fulfills the **Assignment Task: PDF Parsing and Structured JSON Extraction**, meeting requirements for accurate content extraction and correct JSON hierarchy.

---

## 📂 Project Structure

```plaintext
pdf_parser_project/
│── pdf_to_json.py          # Extracts PDF content into structured JSON
│── generate_report.py      # Generates final PDF report from JSON
│── analyze_output.py       # (Optional) Analyzes extracted tables for debugging
│── sample.pdf              # Input PDF (provided by assignment for testing)
│── output_enriched.json    # Extracted structured JSON (output of parser)
│── final_report.pdf        # Final polished report (output of generator)
│── images/                 # Directory for extracted images and generated charts
│   │── page_1_img_1.png    # Extracted chart/image from PDF
│   │── top_holdings.png    # Generated bar chart of top holdings
│   │── performance.png     # Generated bar chart of scheme performance
│   │── inflation_trends.png# Generated bar chart of inflation trends
│   │── nifty_eps.png       # Generated bar chart of Nifty EPS historical trend
│   │── debt_spreads.png    # Generated bar chart of debt spreads
│── requirements.txt        # List of Python dependencies
│── README.md               # Project documentation
        

---

## ⚙️ Installation

### Prerequisites
- Python 3.7+
- Git (for cloning the repository)

### Dependencies
Install the required Python packages using `pip`:
- `pdfplumber`: For text and table extraction from PDFs.
- `PyMuPDF` (fitz): For image extraction from PDFs.
- `pytesseract`: For optional OCR on chart images.
- `Pillow`: For image processing.
- `matplotlib`: For generating charts (e.g., `top_holdings.png`, `performance.png`, `nifty_eps.png`, `debt_spreads.png`).
- `reportlab`: For creating the final PDF report.
- `pandas` and `numpy`: For data analysis (used in `analyze_output.py`).

Install dependencies:
```bash
pip install -r requirements.txt
```

### Tesseract OCR Setup

Required for OCR: Tesseract OCR is needed to extract text from chart images.

**Installation:**
- Download and install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki.
- On Windows: Install to a path like `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- On Linux/Mac: Use package manager (e.g., `sudo apt install tesseract-ocr` on Ubuntu).

**Configuration:** Provide the Tesseract executable path when running the script (see Usage below).

**Verify Installation**
```bash
python -c "import pdfplumber, fitz, pytesseract, PIL, matplotlib, reportlab, pandas, numpy; print('All dependencies installed successfully.')"
```

---

## ▶️ Usage

### 1. Extract PDF to JSON
Run the parser to extract content from the PDF into a structured JSON file:
```bash
python pdf_to_json.py -p sample.pdf -o output_enriched.json -i images --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --ocr
```

**Options:**
- `-p, --pdf`: Path to input PDF file (e.g., sample.pdf, provided in repo).
- `-o, --output`: Path to output JSON file (required).
- `-i, --images`: Directory to save extracted images and generated charts (default: images).
- `--tesseract-cmd`: Path to Tesseract executable for OCR (required if --ocr is used).
- `--ocr`: Enable OCR to extract text from chart images (optional).

**Output:**
- `output_enriched.json` with structured data.
- Extracted images (e.g., page_1_img_1.png) and generated charts (e.g., top_holdings.png, performance.png, nifty_eps.png, debt_spreads.png) in the `images/` folder.

### 2. Generate Final Report
Generate the polished PDF report from the JSON file:
```bash
python generate_report.py
```

**Input:** `output_enriched.json` (must exist in the project directory).  
**Output:** `final_report.pdf` with cover page, tables, and embedded charts (e.g., top_holdings.png, performance.png, nifty_eps.png, debt_spreads.png).

### 3. (Optional) Analyze Extracted Tables
Inspect the extracted tables and generated charts for debugging or manual review:
```bash
python analyze_output.py
```

**Output:** Console log of extracted tables and confirmation of generated charts (e.g., top_holdings.png, performance.png, nifty_eps.png, debt_spreads.png saved).

---

## Features

### Extraction:
- Extracts fund metadata (Fund Name, AUM, Benchmark, Manager, Launch Date).
- Parses tables: Scheme Performance, Portfolio Holdings, Allocation, Risk Metrics, Macro Indicators.
- Extracts charts/images from PDF (e.g., `page_1_img_1.png`) with optional OCR for descriptions.

### Visualization:
Generates charts:
- `top_holdings.png`: Bar chart of top holdings.
- `performance.png`: Bar chart of scheme performance.
- `inflation_trends.png`: Bar chart of inflation trends.
- `nifty_eps.png`: Bar chart of Nifty EPS historical trend.
- `debt_spreads.png`: Bar chart of debt spreads.

### Reporting:
Creates a professional PDF report with:
- Cover page (metadata snapshot).
- Embedded charts (`top_holdings.png`, `performance.png`, `inflation_trends.png`, `nifty_eps.png`, `debt_spreads.png`).
- Tables and a disclaimer section.

---

## Example Workflow
1. Run `pdf_to_json.py` to parse `sample.pdf` into `output_enriched.json`, generating images like `top_holdings.png`, `performance.png`, `inflation_trends.png`, `nifty_eps.png`, and `debt_spreads.png` in `images/`.
2. Run `generate_report.py` to create `final_report.pdf` with embedded charts.
3. Open `final_report.pdf` to review the polished report with charts and tables.

---

## Notes
- **Robustness:** The script handles varying PDF layouts but may require adjustments for complex documents. Test with `sample.pdf`.
- **Limitations:** Chart detection relies on image extraction; OCR may fail with poor image quality.
- **Troubleshooting:**
  - If OCR fails, ensure Tesseract is installed and the `--tesseract-cmd` path is correct.
  - For missing charts, verify data in `output_enriched.json` or check the `images/` folder.

**Assignment Alignment:** Meets the "PDF Parsing and Structured JSON Extraction" requirements:
- Accurate content extraction (metadata, tables, charts).
- Correct JSON hierarchy (pages, sections, data types).

---

## Deliverables (Assignment)
- `pdf_to_json.py`: Script to parse PDF into structured JSON.
- `generate_report.py`: Script to generate the final PDF report.
- `analyze_output.py`: Script to analyze extracted data (optional).
- `sample.pdf`: Provided PDF for testing.
- `output_enriched.json`: Sample extracted JSON file.
- `final_report.pdf`: Sample generated report.
- `requirements.txt`: List of dependencies.
- `README.md`: Comprehensive documentation.

---

##  Repository Link
You can find the complete project on GitHub:  
🔗 [PDF Parsing and Structured JSON Extraction](https://github.com/prasannaedu/-PDF-Parsing-and-Structured-JSON-Extraction-)





