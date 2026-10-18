#!/usr/bin/env python3
"""NEXUS DOWNLOADER – Usage Examples"""

from pathlib import Path
from nexus import download

# Download any file
result = download("https://example.com/file.zip", Path("./downloads"))

# Download Google Drive (handles restrictions)
result = download(
    "https://drive.google.com/file/d/1...",
    Path("./downloads")
)

# Download with proxy
result = download(
    "https://example.com/large-file.iso",
    Path("./downloads"),
    proxy="http://proxy.example.com:8080"
)

# Batch download
for url in ["url1", "url2", "url3"]:
    result = download(url, Path("./downloads"))
    print(f"{'✓' if result else '✗'} {url}")

print("Done!")
