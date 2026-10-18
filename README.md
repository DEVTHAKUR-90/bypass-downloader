# BYPASS DOWNLOADER ⚡

**Universal Unrestricted File Downloader** – Download anything from anywhere, even when access is restricted.

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Status](https://img.shields.io/badge/status-production-brightgreen)

## 🎯 Features

✅ **Google Drive/Docs/Sheets** – Download restricted files, bypass "download disabled"  
✅ **Resume Support** – Continue interrupted downloads from exact byte  
✅ **Stealth Automation** – Headless Selenium with detection bypass  
✅ **Google OAuth2** – Access private/shared restricted files  
✅ **Rate Limiting** – Exponential backoff, proxy rotation, UA cycling  
✅ **Direct Downloads** – HTTP(S) with progress tracking  
✅ **Memory Efficient** – 2MB chunked streaming for large files  
✅ **Production Ready** – 20+ edge cases handled, comprehensive error handling  
✅ **Cross-Platform** – Windows, macOS, Linux  

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/DEVTHAKUR-90/bypass-downloader.git
cd bypass-downloader

# Install
pip install -r requirements.txt

# Run
python bypass.py
```

Then follow prompts:
```
📎 URL: (paste any URL)
📁 Output [cwd]: (folder or leave blank)
🌐 Proxy [none]: (proxy or leave blank)
```

## 📋 Supported URLs

| Type | Example | Works? |
|------|---------|--------|
| **Google Drive** | `https://drive.google.com/file/d/...` | ✓ All restrictions bypassed |
| **Google Docs** | `https://docs.google.com/document/d/...` | ✓ Export as DOCX/PDF/ODT |
| **Google Sheets** | `https://docs.google.com/spreadsheets/d/...` | ✓ Extract all sheets to XLSX |
| **Direct Links** | `https://example.com/file.zip` | ✓ With resume support |
| **Restricted Files** | Private/shared with limits | ✓ Via OAuth2 API |

## 🔄 How It Works

### Google Sheets
1. **Direct Export** → Try standard XLSX export
2. **Google API** → Use authenticated API (handles restrictions)
3. **Selenium** → Extract via headless browser (handles "download disabled")

### Google Drive
1. **Google API** → OAuth2 (handles sharing restrictions)
2. **UC Export** → Direct download link with token
3. **Fallback** → Direct download if public

### Direct Downloads
- **Resume** – Pick up where interrupted
- **Progress** – Real-time speed/ETA
- **Rate Limiting** – Avoid IP bans

## 🐍 Python API

```python
from bypass import download
from pathlib import Path

# Download any file
result = download("https://example.com/file.zip", Path("./downloads"))

# Google Drive (handles restrictions)
result = download(
    "https://drive.google.com/file/d/1...",
    Path("./downloads")
)

# With proxy
result = download(
    url="https://example.com/large-file.iso",
    output=Path("./downloads"),
    proxy="http://proxy.example.com:8080"
)

if result:
    print(f"✓ Downloaded: {result}")
else:
    print("✗ Failed")
```

## 🔐 OAuth2 Setup (Optional)

For accessing private/shared Google files:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project: "Bypass Downloader"
3. Enable Google Drive API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download JSON, save as `credentials.json` in repo directory

See [SETUP.md](SETUP.md) for detailed guide.

## 📦 Installation

### Minimal
```bash
pip install requests urllib3
python bypass.py
```

### Full (Recommended)
```bash
pip install -r requirements.txt
```

This includes:
- `selenium` + `webdriver-manager` – For Sheets extraction
- `google-auth-oauthlib` – For OAuth2
- `pandas` + `openpyxl` – For Excel export

### Docker
```bash
docker build -t bypass-downloader .
docker run -it -v $(pwd)/downloads:/app/downloads bypass-downloader
```

## ⚙️ Configuration

Auto-generated cache:
- `.cache/cookies.pkl` – Session cookies
- `.cache/token.json` – Google OAuth2 token (if used)
- `credentials.json` – Your OAuth2 file (optional)

All can be safely deleted; they're regenerated automatically.

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: selenium` | `pip install selenium webdriver-manager` |
| `ModuleNotFoundError: pandas` | `pip install pandas openpyxl` |
| `credentials.json not found` | Follow OAuth2 setup (optional) |
| `HTTP 403 Forbidden` | Try OAuth2 or use proxy |
| `Timeout` | Check network, try again |
| Chrome not found | Auto-downloaded by webdriver-manager |
| Rate limit exceeded | Add proxy: `export PROXY=http://...` |

## 📚 Examples

```bash
# Download Google Drive file
python bypass.py
# → https://drive.google.com/file/d/1...

# Extract Google Sheets (all sheets)
python bypass.py
# → https://docs.google.com/spreadsheets/d/1...
# Creates: abc12345.xlsx (all sheets preserved)

# Resume interrupted download
python bypass.py
# (runs same command again, resumes from interruption)

# Batch download with Python
python example.py
```

## 📋 Requirements

### Core
- Python 3.8+
- requests >= 2.31.0
- urllib3 >= 2.1.0

### Optional
- selenium >= 4.15.0 + webdriver-manager >= 4.0.0 – For Sheets
- google-auth-oauthlib >= 1.2.0 – For OAuth2
- pandas >= 2.0.0 + openpyxl >= 3.1.0 – For Excel

Install all: `pip install -r requirements.txt`

## 📄 License

MIT License – See [LICENSE](LICENSE)

