"""Build the delivery zip.

Run from anywhere:  python zip_creation.py
Creates CI_GA_Prison.zip next to this file, with everything inside one folder:

  CI_GA_Prison/
    README.txt
    requirements.txt
    report.pdf          (copy of report/main.pdf; compile the report first)
    src/                all the scripts
    results/            all the outputs (tables, CSV files, figures)

The report sources (report/), the web page (web/) and the docs are not included.
"""
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "CI_GA_Prison"
ZIP_PATH = os.path.join(ROOT, f"{NAME}.zip")
SKIP = {"__pycache__", ".DS_Store"}

# (file on disk, path inside the zip)
files = [("README.txt", "README.txt"),
         ("requirements.txt", "requirements.txt"),
         (os.path.join("report", "main.pdf"), "report.pdf")]
for folder in ("src", "results"):
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, folder)):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        for f in sorted(filenames):
            if f not in SKIP and not f.endswith(".pyc"):
                rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
                files.append((rel, rel))

with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for src, dst in files:
        path = os.path.join(ROOT, src)
        if not os.path.exists(path):
            raise FileNotFoundError(f"missing {src}")
        z.write(path, os.path.join(NAME, dst).replace(os.sep, "/"))

print(f"{ZIP_PATH}: {len(files)} files, {os.path.getsize(ZIP_PATH) / 1e6:.1f} MB")
