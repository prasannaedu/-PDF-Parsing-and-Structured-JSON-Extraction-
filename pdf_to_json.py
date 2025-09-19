#!/usr/bin/env python
import os
import io
import json
import argparse
import logging
import re
import hashlib
from typing import List, Any, Dict, Optional, Tuple

import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(line.strip() for line in s.splitlines() if line.strip())


def extract_tables_from_page(pl_page) -> List[List[List[str]]]:
    """Extract tables using pdfplumber and clean them."""
    tables = []
    try:
        raw_tables = pl_page.extract_tables()
        for tbl in raw_tables:
            cleaned = [[("" if c is None else str(c).strip()) for c in row] for row in tbl]
            # drop empty rows
            cleaned = [r for r in cleaned if any(cell != "" for cell in r)]
            if cleaned:
                tables.append(cleaned)
    except Exception as e:
        logging.warning("Table extraction failed: %s", e)
    return tables


def extract_images_with_pymupdf(doc: fitz.Document, page_index: int, images_dir: str) -> List[Dict[str, Any]]:
    """Extract images from a PDF page using PyMuPDF (fitz)."""
    page = doc.load_page(page_index)
    images = page.get_images(full=True)
    results = []
    if not images:
        return results
    os.makedirs(images_dir, exist_ok=True)
    for img_idx, img in enumerate(images, start=1):
        xref = img[0]
        base_name = f"page_{page_index+1}_img_{img_idx}.png"
        path = os.path.join(images_dir, base_name)
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.save(path)
            pix = None
            results.append({"image_path": path, "page_index": page_index + 1})
        except Exception as e:
            logging.warning("Could not extract image on page %d: %s", page_index + 1, e)
    return results


def ocr_image(image_path: str) -> str:
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return clean_text(text)
    except Exception as e:
        logging.warning("OCR failed for %s: %s", image_path, e)
        return ""


# Duplicate image remover helpers (optional)
def file_hash(path, blocksize=65536):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        buf = f.read(blocksize)
        while buf:
            hasher.update(buf)
            buf = f.read(blocksize)
    return hasher.hexdigest()


def remove_duplicate_images(images_dir: str):
    if not os.path.exists(images_dir):
        return
    seen = {}
    removed = 0
    for fname in os.listdir(images_dir):
        fpath = os.path.join(images_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            h = file_hash(fpath)
            if h in seen:
                os.remove(fpath)
                removed += 1
            else:
                seen[h] = fpath
        except Exception as e:
            logging.warning("Error hashing file %s: %s", fpath, e)
    if removed:
        logging.info("🧹 Removed %d duplicate images from %s", removed, images_dir)


def detect_sections_from_text(text: str) -> List[Dict[str, Any]]:
    """Detect main sections and subsections from a text block."""
    if not text:
        return []

    lines = [ln.rstrip() for ln in text.splitlines()]
    result = []
    current_section = None
    current_subsection = None
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # main section detection: often ALL CAPS headings
        if (line.isupper() and len(line) < 120) or re.match(r'^#\s+[A-Z]', line):
            if current_section and current_text:
                result.append({
                    "type": "paragraph",
                    "section": current_section,
                    "sub_section": current_subsection,
                    "text": clean_text("\n".join(current_text))
                })
                current_text = []
            current_section = line.replace('#', '').strip()
            current_subsection = None

        # subsections: lines with colon
        elif re.match(r'^[A-Za-z][A-Za-z\s]+:', line) and len(line) < 120:
            if current_section and current_text:
                result.append({
                    "type": "paragraph",
                    "section": current_section,
                    "sub_section": current_subsection,
                    "text": clean_text("\n".join(current_text))
                })
                current_text = []
            current_subsection = line

        else:
            current_text.append(line)

    if current_section and current_text:
        result.append({
            "type": "paragraph",
            "section": current_section,
            "sub_section": current_subsection,
            "text": clean_text("\n".join(current_text))
        })

    return result


def classify_table(table: List[List[str]]) -> Tuple[Optional[str], Optional[str]]:
    """
    Classify table into one of:
      - portfolio (holdings)
      - allocation
      - scheme_performance
      - risk
      - macro
    This classifier is intentionally relaxed/robust to catch more table headers.
    """
    if not table or len(table) < 1:
        return None, None

    header = [str(c).lower() for c in table[0]]
    header_str = " ".join(header)

    # scheme performance (explicit)
    if "scheme performance" in header_str or ("performance" in header_str and "scheme" in header_str) or "ptp" in header_str or "last 1 year" in header_str or "since inception" in header_str:
        return "scheme_performance", "Performance Data"

    # SIP / 'if you had invested' style performance
    if "sip" in header_str or "if you had invested" in header_str:
        return "scheme_performance", "SIP Performance"

    # portfolio/holdings: look for company/issuer/instrument/sector/weight/%
    if any(x in header_str for x in ["company", "issuer", "instrument", "name", "sector", "%", "weight", "net assets"]):
        # if 'debt' or 'credit rating' present, tag as debt_portfolio optionally
        if "debt" in header_str or "credit rating" in header_str:
            return "debt_portfolio", "Debt Holdings"
        return "portfolio", "Holdings"

    # allocation
    if any(x in header_str for x in ["sector allocation", "group allocation", "market capitalisation", "allocation"]):
        return "allocation", "Allocation Data"

    # risk metrics
    if any(x in header_str for x in ["riskometer", "risk profile", "std. dev", "beta", "sharpe", "treynor", "risk"]):
        return "risk", "Risk Metrics"

    # macro / economic
    if any(x in header_str for x in ["macro", "economic", "indicators", "gdp", "inflation"]):
        return "macro", "Economic Indicators"

    return None, None


def extract_metadata(pdf_path: str) -> Dict[str, str]:
    """Scan the document for basic metadata (fund name, aum, benchmark, manager, launch)."""
    metadata = {
        "fund_name": "N/A",
        "aum": "N/A",
        "benchmark": "N/A",
        "additional_benchmark": "N/A",
        "fund_manager": "N/A",
        "launch_date": "N/A"
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            for line in lines:
                low = line.lower()
                # skip disclaimers
                if any(x in low for x in ["disclaimer", "page |", "mutual fund:"]):
                    continue
                # fund name pattern (caps, ends with FUND)
                if metadata["fund_name"] == "N/A" and re.match(r'^[A-Z][A-Z\s]+(FUND|SCHEME)', line):
                    metadata["fund_name"] = line
                # aum
                if metadata["aum"] == "N/A" and ("aum" in low or "assets under management" in low):
                    m = re.search(r'([\d,\.]+\s*(cr|crore|lakh|million|billion))', line, re.IGNORECASE)
                    if m:
                        metadata["aum"] = m.group(1)
                # benchmark lines
                if "benchmark" in low:
                    # try capture after colon
                    if ":" in line:
                        parts = line.split(":", 1)
                        name = parts[1].strip()
                    else:
                        name = line.strip()
                    if "additional" in low:
                        if metadata["additional_benchmark"] == "N/A":
                            metadata["additional_benchmark"] = name
                    else:
                        if metadata["benchmark"] == "N/A":
                            metadata["benchmark"] = name
                # fund manager
                if "fund manager" in low and metadata["fund_manager"] == "N/A":
                    if ":" in line:
                        metadata["fund_manager"] = line.split(":", 1)[1].strip()
                    else:
                        metadata["fund_manager"] = line.strip()
                # launch date
                if ("launch" in low or "inception" in low) and metadata["launch_date"] == "N/A":
                    date_match = re.search(r'(\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', line, re.IGNORECASE)
                    if date_match:
                        metadata["launch_date"] = date_match.group(1)

    return metadata


def parse_pdf_to_json(pdf_path: str, output_json: str, images_dir: str = "images", do_ocr: bool = False):
    logging.info("Opening PDF: %s", pdf_path)
    metadata = extract_metadata(pdf_path)

    result = {
        "metadata": metadata,
        "sections": {
            "portfolio": [],
            "scheme_performance": [],
            "allocation": [],
            "risk": [],
            "macro": [],
            "debt_portfolio": []
        },
        "pages": []
    }

    with pdfplumber.open(pdf_path) as plpdf:
        doc = fitz.open(pdf_path)
        num_pages = len(plpdf.pages)
        logging.info("Number of pages detected: %d", num_pages)

        for i, pl_page in enumerate(plpdf.pages):
            page_no = i + 1
            page_entry = {"page_number": page_no, "content": []}

            text = pl_page.extract_text() or ""
            sections = detect_sections_from_text(text)
            page_entry["content"].extend(sections)

            tables = extract_tables_from_page(pl_page)
            for tbl in tables:
                section_type, section_name = classify_table(tbl)
                if section_type:
                    result["sections"].setdefault(section_type, []).append({
                        "page": page_no,
                        "table_data": tbl,
                        "section_name": section_name
                    })
                page_entry["content"].append({
                    "type": "table",
                    "section": section_name,
                    "table_data": tbl
                })

            images_meta = extract_images_with_pymupdf(doc, i, images_dir)
            for img_meta in images_meta:
                description = ocr_image(img_meta["image_path"]) if do_ocr else None
                page_entry["content"].append({
                    "type": "chart",
                    "image": img_meta["image_path"],
                    "description": description
                })

            result["pages"].append(page_entry)

    # optional: remove duplicate extracted images
    try:
        remove_duplicate_images(images_dir)
    except Exception:
        pass

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logging.info("✅ Enriched JSON saved to %s", output_json)


def main():
    parser = argparse.ArgumentParser(description="PDF → structured JSON extractor for mutual fund documents")
    parser.add_argument("--pdf", "-p", required=True, help="Path to input PDF")
    parser.add_argument("--output", "-o", required=True, help="Path to output JSON file")
    parser.add_argument("--images", "-i", default="images", help="Directory to save extracted images")
    parser.add_argument("--ocr", action="store_true", help="Run OCR on extracted images")
    parser.add_argument("--tesseract-cmd", default=None, help="Path to tesseract executable")
    args = parser.parse_args()

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd

    parse_pdf_to_json(args.pdf, args.output, images_dir=args.images, do_ocr=args.ocr)


if __name__ == "__main__":
    main()