#!/usr/bin/env python3
"""
Download separate boys/girls OSAA tennis PDFs for years that use {year}b.pdf and {year}g.pdf format.
Then OCR them and merge into the text directory.
"""
import os
import sys
import time
import subprocess
import urllib.request
import fitz

PDF_DIR = "/tmp/osaa_pdfs"
TEXT_DIR = "/tmp/osaa_text"

# Years that had 404s at {year}.pdf - try b/g format
MISSING_YEARS = list(range(1973, 1989)) + list(range(1993, 2007))

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        # Check if it's actually a PDF
        with open(path, 'rb') as f:
            header = f.read(4)
        if header == b'%PDF':
            return True
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            ct = resp.headers.get('Content-Type', '')
            if 'pdf' not in ct.lower():
                return False
            data = resp.read()
            with open(path, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        return False


def ocr_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except:
        return ""
    full_text = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if len(text) > 50:
            full_text.append(text)
            continue
        try:
            pix = page.get_pixmap(dpi=300)
            img_path = f"/tmp/osaa_ocr_temp_{i}.png"
            pix.save(img_path)
            result = subprocess.run(
                ["tesseract", img_path, "stdout"],
                capture_output=True, text=True, timeout=60
            )
            full_text.append(result.stdout)
            os.remove(img_path)
        except:
            pass
    return "\n".join(full_text)


def main():
    found_catlin = []

    for year in MISSING_YEARS:
        sys.stdout.write(f"\r  Processing {year}...")
        sys.stdout.flush()

        boys_pdf = os.path.join(PDF_DIR, f"{year}b.pdf")
        girls_pdf = os.path.join(PDF_DIR, f"{year}g.pdf")
        boys_url = f"https://www.osaa.org/docs/btn/records/{year}b.pdf"
        girls_url = f"https://www.osaa.org/docs/btn/records/{year}g.pdf"

        boys_ok = download(boys_url, boys_pdf)
        girls_ok = download(girls_url, girls_pdf)

        if not boys_ok and not girls_ok:
            continue

        combined_text = ""
        if boys_ok:
            text = ocr_pdf(boys_pdf)
            combined_text += "BOYS\n" + text + "\n\n"
        if girls_ok:
            text = ocr_pdf(girls_pdf)
            combined_text += "GIRLS\n" + text + "\n\n"

        # Save combined text (overwrite any 404 page text)
        text_path = os.path.join(TEXT_DIR, f"{year}.txt")
        with open(text_path, "w") as f:
            f.write(f"TENNIS {year}\n\n{combined_text}")

        # Check for Catlin
        if "catlin" in combined_text.lower():
            found_catlin.append(year)
            print(f"\n  *** {year}: Found Catlin Gabel! ***")

        time.sleep(0.3)

    print(f"\n\nYears with separate b/g PDFs containing Catlin Gabel: {found_catlin}")
    print(f"Total new years found: {len(found_catlin)}")


if __name__ == "__main__":
    main()
