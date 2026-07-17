"""
Runlog scanner for ??? adoption.
"""

import csv
import glob
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import unquote_plus

import fitz

TARGET = "???"
TARGET_LOWER = TARGET.lower()

CUTOFF_DATE = datetime(2026, 6, 6)

MAX_WORKERS = 32

MARKETS = ["br", "go", "hk", "ib", "id", "jp", "my", "ph", "sg", "th", "vn"]

ENVS = ["preprod", "prod"]

NO_COMPARTMENT = {("go", "prod")}


def env_subfolder(market, env):

    return f"{market.upper()}-{'Preprod' if env == 'preprod' else 'Prod'}"


def runlog_pattern(market, env):

    base = (
        rf"\\{market}.fsx.{env}.sth.sth"
        rf"\PE_Data\{env_subfolder(market, env)}"
        rf"\PE_Results"
    )

    if (market, env) in NO_COMPARTMENT:
        return base + r"\*\jobs\*\results\runlog.pdf"

    return base + r"\Compartment_*\*\jobs\*\results\runlog.pdf"


PATTERNS = [runlog_pattern(market, env) for market in MARKETS for env in ENVS]

CSV_FILE = "???.csv"

STANDARD_PATH_RE = re.compile(
    r"\\(?P<entity>[a-z]{2})\.fsx\.[^\\]+\\PE_Data\\[^\\]+\\PE_Results\\Compartment_\d+\\(?P<workspace>.+?)\\jobs\\(?P<job>.+?)\\results\\runlog\.pdf$",
    re.IGNORECASE,
)

GO_PROD_PATH_RE = re.compile(
    r"\\(?P<entity>[a-z]{2})\.fsx\.[^\\]+\\PE_Data\\[^\\]+\\PE_Results\\(?P<workspace>.+?)\\jobs\\(?P<job>.+?)\\results\\runlog\.pdf$",
    re.IGNORECASE,
)


def extract_path_details(pdf_path):
    match = STANDARD_PATH_RE.search(pdf_path)
    if not match:
        match = GO_PROD_PATH_RE.search(pdf_path)

    if not match:
        return "", "", ""

    entity = match.group("entity").lower()
    workspace = unquote_plus(match.group("workspace")).strip()
    job_name = unquote_plus(match.group("job")).strip()

    job_name = re.sub(r"_\d+$", "", job_name)

    return (entity, workspace, job_name)


def scan_pdf(pdf_path):
    """Scan one PDF runlog."""
    try:
        modified_time = os.path.getmtime(pdf_path)

        modified_datetime = datetime.fromtimestamp(modified_time)

        if modified_datetime < CUTOFF_DATE:
            return None

        timestamp = modified_datetime.strftime("%Y-%m-%d %H:%M:%S")

        entity, workspace, job_name = extract_path_details(pdf_path)

        doc = fitz.open(pdf_path)

        found_target = False

        for page in doc:
            page_text = page.get_text()

            if TARGET_LOWER in page_text.lower():
                found_target = True
                break

        doc.close()

        if found_target:
            return (timestamp, entity, workspace, job_name, "FOUND", pdf_path)

        return (timestamp, entity, workspace, job_name, "OUTDATED", pdf_path)

    except Exception as e:
        return ("", "", "", "", f"ERROR: {e}", pdf_path)


overall_start = time.perf_counter()

print("========================================")
print("Discovering runlogs...")
print("========================================")

discovery_start = time.perf_counter()

pdf_paths = []

for pattern in PATTERNS:
    print(f"Pattern: {pattern}")

    matches = glob.glob(pattern)

    pdf_paths.extend(matches)

discovery_end = time.perf_counter()

print(f"\nRunlogs discovered: {len(pdf_paths):,}")

print(f"Discovery Time: {discovery_end - discovery_start:.2f} seconds")

found = 0
outdated = 0
errors = 0
processed = 0

scan_start = time.perf_counter()

with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)

    writer.writerow(
        ["Timestamp", "Entity", "Workspace", "Job_Name", "Status", "PDF_Path"]
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for result in executor.map(scan_pdf, pdf_paths, chunksize=100):
            if result is None:
                continue

            (timestamp, entity, workspace, job_name, status, pdf_path) = result

            writer.writerow([timestamp, entity, workspace, job_name, status, pdf_path])

            processed += 1

            if status == "FOUND":
                found += 1

            elif status == "OUTDATED":
                outdated += 1

            else:
                errors += 1

            if processed % 100 == 0:
                print(f"Processed {processed:,} runlogs...")

scan_end = time.perf_counter()

overall_end = time.perf_counter()

print("\n========================================")
print("               SUMMARY")
print("========================================")

print(f"Runlogs Discovered    : {len(pdf_paths):,}")
print(f"Runlogs Processed     : {processed:,}")
print(f"FOUND                 : {found:,}")
print(f"OUTDATED              : {outdated:,}")
print(f"ERRORS                : {errors:,}")

print("========================================")

print(f"Discovery Time        : {discovery_end - discovery_start:.2f} sec")

print(f"Scanning Time         : {scan_end - scan_start:.2f} sec")

print(f"Total Runtime         : {overall_end - overall_start:.2f} sec")

print("========================================")

print(f"\nCSV Report Generated: {CSV_FILE}")
