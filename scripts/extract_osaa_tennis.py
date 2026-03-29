#!/usr/bin/env python3
"""
Download OSAA tennis records PDFs and extract Catlin Gabel mentions via OCR.
URL pattern: https://www.osaa.org/docs/btn/records/{year}.pdf
"""

import fitz
import subprocess
import os
import sys
import time
import json
import urllib.request

PDF_DIR = "/tmp/osaa_pdfs"
TEXT_DIR = "/tmp/osaa_text"
RESULTS_FILE = "/home/user/viperball/data/catlin_gabel_tennis_qualifiers.txt"
RESULTS_JSON = "/home/user/viperball/data/catlin_gabel_tennis_qualifiers.json"

# Catlin Gabel has been around since the 1960s but tennis program likely started later.
# The banners show earliest championship in 1985. Let's go wide: 1960-2025.
START_YEAR = 1960
END_YEAR = 2025

SEARCH_TERMS = ["catlin gabel", "catlin", "c. gabel", "c gabel"]

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)


def download_pdf(year):
    """Download a single year's PDF. Returns path or None."""
    url = f"https://www.osaa.org/docs/btn/records/{year}.pdf"
    path = os.path.join(PDF_DIR, f"{year}.pdf")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) < 500:
                return None
            with open(path, "wb") as f:
                f.write(data)
            return path
    except Exception as e:
        print(f"  [{year}] Download failed: {e}", file=sys.stderr)
        return None


def pdf_to_text(pdf_path, year):
    """Extract text from PDF via OCR. Returns full text string."""
    text_path = os.path.join(TEXT_DIR, f"{year}.txt")
    if os.path.exists(text_path):
        with open(text_path) as f:
            return f.read()

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  [{year}] Can't open PDF: {e}", file=sys.stderr)
        return ""

    full_text = []
    for i, page in enumerate(doc):
        # First try direct text extraction
        text = page.get_text().strip()
        if len(text) > 50:
            full_text.append(text)
            continue

        # Fall back to OCR
        try:
            pix = page.get_pixmap(dpi=300)
            img_path = f"/tmp/osaa_page_{year}_{i}.png"
            pix.save(img_path)
            result = subprocess.run(
                ["tesseract", img_path, "stdout"],
                capture_output=True, text=True, timeout=60
            )
            full_text.append(result.stdout)
            os.remove(img_path)
        except Exception as e:
            print(f"  [{year}] OCR failed page {i}: {e}", file=sys.stderr)

    combined = "\n".join(full_text)
    with open(text_path, "w") as f:
        f.write(combined)
    return combined


def find_tennis_section(text):
    """Extract the tennis portion of the text."""
    text_upper = text.upper()
    # Find TENNIS header
    idx = text_upper.find("TENNIS")
    if idx == -1:
        return text  # Return all text if no clear tennis section
    # Find the next sport section after tennis (common headers)
    next_sports = ["TRACK", "BASEBALL", "SOFTBALL", "GOLF", "SWIMMING", "WRESTLING",
                   "BASKETBALL", "FOOTBALL", "VOLLEYBALL", "SOCCER", "CROSS COUNTRY"]
    end_idx = len(text)
    for sport in next_sports:
        pos = text_upper.find(sport, idx + 10)
        if pos != -1 and pos < end_idx:
            end_idx = pos
    return text[idx:end_idx]


def search_for_catlin(text, year):
    """Search text for Catlin Gabel references. Returns list of matching lines with context."""
    text_lower = text.lower()
    matches = []
    lines = text.split("\n")

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if not line_lower:
            continue
        for term in SEARCH_TERMS:
            if term in line_lower:
                # Get surrounding context (2 lines before and after)
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                context = "\n".join(lines[start:end])
                matches.append({
                    "line": line.strip(),
                    "context": context.strip(),
                    "term_matched": term
                })
                break
    return matches


def main():
    print(f"=== OSAA Tennis Records Extraction for Catlin Gabel ===")
    print(f"Scanning years {START_YEAR}-{END_YEAR}\n")

    all_results = {}
    years_with_data = []
    years_no_pdf = []

    for year in range(START_YEAR, END_YEAR + 1):
        sys.stdout.write(f"\r  Processing {year}...")
        sys.stdout.flush()

        # Download
        pdf_path = download_pdf(year)
        if not pdf_path:
            years_no_pdf.append(year)
            continue

        # OCR
        text = pdf_to_text(pdf_path, year)
        if not text.strip():
            continue

        # Find tennis section
        tennis_text = find_tennis_section(text)

        # Search for Catlin Gabel
        matches = search_for_catlin(tennis_text, year)
        if matches:
            all_results[year] = {
                "matches": matches,
                "tennis_section_preview": tennis_text[:500]
            }
            years_with_data.append(year)
            print(f"\n  *** {year}: Found {len(matches)} Catlin Gabel mention(s)! ***")

        # Be nice to the server
        time.sleep(0.3)

    print(f"\n\n=== SUMMARY ===")
    print(f"Years scanned: {START_YEAR}-{END_YEAR}")
    print(f"Years with no PDF available: {len(years_no_pdf)}")
    print(f"Years with Catlin Gabel mentions: {len(years_with_data)}")
    print(f"Years: {years_with_data}")

    # Write results
    with open(RESULTS_JSON, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nJSON results saved to: {RESULTS_JSON}")

    # Write human-readable results
    with open(RESULTS_FILE, "w") as f:
        f.write("CATLIN GABEL TENNIS - OSAA STATE QUALIFIERS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Extracted from OSAA records PDFs ({START_YEAR}-{END_YEAR})\n\n")
        for year in sorted(all_results.keys()):
            f.write(f"\n{'='*60}\n")
            f.write(f"YEAR: {year}\n")
            f.write(f"{'='*60}\n")
            for match in all_results[year]["matches"]:
                f.write(f"\nMatched line: {match['line']}\n")
                f.write(f"Context:\n{match['context']}\n")
                f.write("-" * 40 + "\n")
    print(f"Text results saved to: {RESULTS_FILE}")

    # Also dump all tennis text for years with Catlin Gabel for manual review
    detail_file = "/home/user/viperball/data/catlin_gabel_tennis_detail.txt"
    with open(detail_file, "w") as f:
        for year in sorted(all_results.keys()):
            f.write(f"\n{'#'*60}\n")
            f.write(f"# YEAR: {year}\n")
            f.write(f"{'#'*60}\n")
            # Re-read full tennis text
            text_path = os.path.join(TEXT_DIR, f"{year}.txt")
            if os.path.exists(text_path):
                with open(text_path) as tf:
                    full_text = tf.read()
                tennis = find_tennis_section(full_text)
                f.write(tennis + "\n")
    print(f"Detailed tennis sections saved to: {detail_file}")


if __name__ == "__main__":
    main()
