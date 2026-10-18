#!/usr/bin/env python3
"""
BYPASS DOWNLOADER - Universal Unrestricted File Downloader
Download anything: Google Drive/Docs/Sheets (restricted), direct links, OAuth2.
Production-ready with comprehensive error handling, resume support, stealth automation.

Author: iamdev904590@gmail.com | License: MIT | Repo: https://github.com/DEVTHAKUR-90/bypass-downloader
"""

import re
import json
import time
import logging
import os
import sys
import hashlib
import pickle
import atexit
import signal
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as URLRetry
import random

# ============= OPTIONAL DEPENDENCIES =============
SELENIUM_AVAILABLE = GOOGLE_API_AVAILABLE = PANDAS_AVAILABLE = OPENPYXL_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, StaleElementReferenceException,
        WebDriverException, InvalidSessionIdException
    )
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_API_AVAILABLE = True
except ImportError:
    pass

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    pass

# ============= CONFIG =============
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

CHUNK_SIZE = 2 * 1024 * 1024
TIMEOUT_CONN = 30
TIMEOUT_READ = 600
MAX_RETRIES = 7
BACKOFF_FACTOR = 2.0
MIN_FILE_SIZE = 100

# ============= LOGGING =============
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
        'ERROR': '\033[31m', 'CRITICAL': '\033[35m', 'RESET': '\033[0m',
    }
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}[{record.levelname}]{self.COLORS['RESET']}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
log = logging.getLogger("bypass")
log.handlers.clear()
log.addHandler(handler)
log.setLevel(logging.INFO)

# ============= RESOURCE CLEANUP =============
_drivers = []
_sessions = []

def _cleanup():
    for d in _drivers:
        try: d.quit()
        except: pass
    for s in _sessions:
        try: s.close()
        except: pass

atexit.register(_cleanup)
signal.signal(signal.SIGINT, lambda *_: (log.warning("\nInterrupted"), _cleanup(), sys.exit(1)))

# ============= VALIDATION =============
def validate_url(url: str) -> bool:
    try: return all([urlparse(url).scheme, urlparse(url).netloc])
    except: return False

def validate_path(p: Path) -> bool:
    try:
        if p.exists(): return True
        parent = p.parent if p.suffix else p
        return parent.exists() or parent.parent.exists()
    except: return False

# ============= SESSION =============
class Session:
    def __init__(self, proxy: str = None):
        self.session = requests.Session()
        self.proxy = proxy
        self.last_request = 0
        self.ua_index = 0
        self.cookies_file = Path(".cache/cookies.pkl")
        self.cookies_file.parent.mkdir(exist_ok=True)
        self._setup()
        self._load_cookies()
        _sessions.append(self.session)
    
    def _setup(self):
        retry = URLRetry(
            total=MAX_RETRIES, backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        if self.proxy:
            self.session.proxies.update({"http": self.proxy, "https": self.proxy})
        self._set_headers()
    
    def _set_headers(self):
        ua = USER_AGENTS[self.ua_index % len(USER_AGENTS)]
        self.ua_index += 1
        self.session.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        })
    
    def _load_cookies(self):
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'rb') as f:
                    self.session.cookies.update(pickle.load(f))
        except: pass
    
    def _save_cookies(self):
        try:
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(self.session.cookies, f)
        except: pass
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < 1.5:
            time.sleep(max(0, 1.5 - elapsed + random.uniform(0, 0.5)))
        self.last_request = time.time()
    
    def get(self, url: str, **kwargs):
        self._rate_limit()
        self._set_headers()
        try:
            resp = self.session.get(url, timeout=(TIMEOUT_CONN, TIMEOUT_READ), verify=True, **kwargs)
            self._save_cookies()
            return resp
        except Exception as e:
            log.debug(f"GET failed: {e}")
            return None
    
    def head(self, url: str, **kwargs):
        self._set_headers()
        try:
            return self.session.head(url, timeout=(TIMEOUT_CONN, TIMEOUT_CONN), verify=True, **kwargs)
        except Exception: return None
    
    def close(self):
        try: self.session.close()
        except: pass

# ============= URL HELPERS =============
def extract_file_id(url: str) -> Optional[str]:
    if not url: return None
    for p in [r"/d/([a-zA-Z0-9_-]{20,})", r"[?&]id=([a-zA-Z0-9_-]{20,})", 
              r"spreadsheets/d/([a-zA-Z0-9_-]{20,})", r"document/d/([a-zA-Z0-9_-]{20,})",
              r"presentation/d/([a-zA-Z0-9_-]{20,})"]:
        try:
            m = re.search(p, url)
            if m: return m.group(1)
        except: pass
    return None

is_google_sheets = lambda u: u and "docs.google.com/spreadsheets" in u
is_google_docs = lambda u: u and "docs.google.com/document" in u
is_google_drive = lambda u: u and ("drive.google.com" in u or "docs.google.com" in u)

# ============= DOWNLOAD FUNCTIONS =============
def download_resume(url: str, output: Path, proxy: str = None) -> Optional[Path]:
    if not validate_url(url):
        log.error("Invalid URL")
        return None
    
    session = Session(proxy=proxy)
    try:
        log.info(f"Probing: {url[:60]}...")
        head = session.head(url)
        if not head or head.status_code >= 400:
            log.error(f"HEAD failed: {head.status_code if head else 'No response'}")
            return None
        
        total = int(head.headers.get('content-length', 0))
        resume = 'accept-ranges' in head.headers.get('accept-ranges', '').lower()
        
        if total > 0:
            log.info(f"Size: {total / (1024**2):.2f}MB | Resume: {'✓' if resume else '✗'}")
        
        name = url.split('/')[-1].split('?')[0]
        if not name or '.' not in name:
            ct = head.headers.get('content-type', '')
            ext = next((e for k, e in [
                ('application/pdf', '.pdf'),
                ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
                ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
                ('application/zip', '.zip'),
            ] if k in ct), '.bin')
            name = f"download{ext}"
        
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        final = output / name if output.is_dir() else output
        
        if final.exists():
            existing = final.stat().st_size
            if existing < total and resume:
                log.info(f"Resuming: {existing}/{total}")
                mode, headers = 'ab', {'Range': f'bytes={existing}-'}
            else:
                mode, headers = 'wb', {}
        else:
            mode, headers = 'wb', {}
        
        resp = session.get(url, stream=True, headers=headers)
        if not resp or resp.status_code not in [200, 206]:
            log.error(f"Download failed: HTTP {resp.status_code if resp else 'timeout'}")
            return None
        
        if 'text/html' in resp.headers.get('content-type', ''):
            log.error("Received HTML (possibly blocked)")
            return None
        
        downloaded = 0 if mode == 'wb' else final.stat().st_size
        last_log = 0
        
        try:
            with open(final, mode) as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0 and downloaded - last_log > 50 * CHUNK_SIZE:
                            log.info(f"Progress: {(downloaded/total)*100:.1f}%")
                            last_log = downloaded
        except IOError as e:
            log.error(f"Write error: {e}")
            return None
        
        if final.stat().st_size < MIN_FILE_SIZE:
            log.error(f"File too small ({final.stat().st_size} bytes)")
            final.unlink()
            return None
        
        log.info(f"✓ Downloaded: {final}")
        return final
    
    except Exception as e:
        log.error(f"Download error: {e}")
        return None
    finally:
        session.close()

def extract_sheets_selenium(url: str, file_id: str, output: Path) -> Optional[Path]:
    if not SELENIUM_AVAILABLE:
        log.error("Selenium required: pip install selenium webdriver-manager")
        return None
    if not PANDAS_AVAILABLE or not OPENPYXL_AVAILABLE:
        log.error("pandas + openpyxl required: pip install pandas openpyxl")
        return None
    
    driver = None
    try:
        log.info("Starting Selenium...")
        opts = ChromeOptions()
        for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled", "--start-maximized"]:
            opts.add_argument(arg)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        
        try:
            driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=opts
            )
        except:
            log.warning("Chrome failed, trying Firefox...")
            fopts = FirefoxOptions()
            fopts.add_argument("--headless")
            driver = webdriver.Firefox(
                service=webdriver.firefox.service.Service(GeckoDriverManager().install()),
                options=fopts
            )
        
        _drivers.append(driver)
        driver.set_page_load_timeout(30)
        driver.get(f"https://docs.google.com/spreadsheets/d/{file_id}/edit")
        time.sleep(6)
        
        sheets = []
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@role='tab']"))
            )
            for tab in driver.find_elements(By.XPATH, "//div[@role='tab']"):
                try:
                    name = tab.text.strip()
                    if name and len(name) < 100:
                        sheets.append(name)
                except (StaleElementReferenceException, NoSuchElementException):
                    pass
        except TimeoutException:
            sheets = ["Sheet1"]
        
        if not sheets: sheets = ["Sheet1"]
        log.info(f"Found sheets: {sheets}")
        
        sheets_data = {}
        for sname in sheets:
            try:
                log.info(f"Extracting: {sname}")
                driver.execute_script(f"""
                for (var t of document.querySelectorAll('div[role="tab"]')) {{
                    if (t.innerText.trim() === '{sname}') {{ t.click(); break; }}
                }}
                """)
                time.sleep(3)
                
                data = driver.execute_script("""
                var cells = document.querySelectorAll('[role="gridcell"]');
                var map = {}, rows = {};
                cells.forEach(c => {
                    try {
                        var r = c.getBoundingClientRect();
                        map[Math.round(r.top) + "," + Math.round(r.left)] = c.innerText || '';
                    } catch(e) {}
                });
                for (var k in map) {
                    var [y, x] = k.split(",");
                    if (!rows[y]) rows[y] = {};
                    rows[y][x] = map[k];
                }
                var result = [];
                Object.keys(rows).sort((a, b) => a - b).forEach(y => {
                    var cols = [];
                    Object.keys(rows[y]).sort((a, b) => a - b).forEach(x => {
                        cols.push(rows[y][x]);
                    });
                    result.push(cols);
                });
                return result;
                """)
                
                if data and len(data) > 0:
                    sheets_data[sname] = data
                    log.info(f"  ✓ {len(data)} rows")
                else:
                    log.warning(f"  ✗ No data")
            except Exception as e:
                log.warning(f"  Error: {e}")
        
        if not sheets_data:
            log.error("No sheets extracted")
            return None
        
        try:
            excel = output / f"{file_id[:8]}.xlsx"
            with pd.ExcelWriter(excel, engine='openpyxl') as w:
                for sname, data in sheets_data.items():
                    try:
                        df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame(data)
                        df.to_excel(w, sheet_name=sname[:31], index=False)
                    except Exception as e:
                        log.warning(f"Write error: {e}")
            
            log.info(f"✓ Exported to {excel}")
            return excel
        except Exception as e:
            log.error(f"Excel export failed: {e}")
            return None
    
    except Exception as e:
        log.error(f"Selenium failed: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
                _drivers.remove(driver)
            except: pass

def download_google_api(file_id: str, output: Path) -> Optional[Path]:
    if not GOOGLE_API_AVAILABLE: return None
    
    try:
        creds = None
        token_file = Path(".cache/token.json")
        creds_file = Path("credentials.json")
        token_file.parent.mkdir(exist_ok=True)
        
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(token_file)
            except:
                token_file.unlink()
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try: creds.refresh(Request())
                except: token_file.unlink(); creds = None
            
            if not creds and creds_file.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        creds_file, scopes=['https://www.googleapis.com/auth/drive']
                    )
                    creds = flow.run_local_server(port=0, open_browser=True)
                except Exception as e:
                    log.warning(f"OAuth failed: {e}")
                    return None
            else:
                return None
            
            if creds:
                try:
                    with open(token_file, 'w') as f:
                        f.write(creds.to_json())
                except: pass
        
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        meta = service.files().get(fileId=file_id, fields='name, mimeType').execute()
        
        name = meta.get('name', f'file_{file_id[:8]}')
        mime = meta.get('mimeType', '')
        
        if 'vnd.google-apps' in mime:
            for key, (export_mime, ext) in [
                ('vnd.google-apps.document', ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')),
                ('vnd.google-apps.spreadsheet', ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')),
                ('vnd.google-apps.presentation', ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')),
            ]:
                if key in mime:
                    request = service.files().export_media(fileId=file_id, mimeType=export_mime)
                    name = Path(name).stem + ext
                    break
            else:
                log.warning("Unsupported Google doc type")
                return None
        else:
            request = service.files().get_media(fileId=file_id)
        
        final = output / name if output.is_dir() else output
        
        log.info("Downloading via API...")
        with open(final, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=CHUNK_SIZE)
            done = False
            while not done:
                try:
                    status, done = downloader.next_chunk()
                    if status:
                        log.info(f"API: {int(status.progress() * 100)}%")
                except HttpError as e:
                    log.error(f"API error: {e}")
                    return None
        
        log.info(f"✓ API download: {final}")
        return final
    
    except Exception as e:
        log.warning(f"API failed: {e}")
        return None

def download_google_drive_uc(file_id: str, output: Path, proxy: str = None) -> Optional[Path]:
    session = Session(proxy=proxy)
    try:
        log.info("Trying UC export...")
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        resp = session.get(url)
        if not resp: return None
        
        for key, val in resp.cookies.items():
            if 'download' in key.lower():
                resp = session.get(url + f"&confirm={val}", stream=True)
                break
        
        if not resp or 'text/html' in resp.headers.get('content-type', ''):
            return None
        
        name = resp.headers.get('content-disposition', '').split('filename=')[-1].strip('"')
        if not name: name = f"gdrive_{file_id[:8]}"
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        
        final = output / name if output.is_dir() else output
        
        with open(final, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if chunk: f.write(chunk)
        
        if final.stat().st_size < MIN_FILE_SIZE:
            log.error("File too small")
            final.unlink()
            return None
        
        log.info(f"✓ UC export: {final}")
        return final
    
    except Exception as e:
        log.warning(f"UC failed: {e}")
        return None
    finally:
        session.close()

# ============= MAIN =============
def download(url: str, output: Path = None, proxy: str = None) -> Optional[Path]:
    if not validate_url(url):
        log.error("Invalid URL")
        return None
    
    if output is None: output = Path.cwd()
    
    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.error(f"Cannot create directory: {e}")
        return None
    
    if not validate_path(output):
        log.error("Invalid output path")
        return None
    
    file_id = extract_file_id(url) if is_google_drive(url) else None
    
    # Google Sheets
    if is_google_sheets(url) and file_id:
        log.info(">>> Google Sheets")
        log.info("[1/4] Direct export...")
        session = Session(proxy=proxy)
        try:
            r = session.get(f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx")
            if r and r.status_code == 200 and 'text/html' not in r.headers.get('content-type', ''):
                final = output / f"{file_id[:8]}.xlsx"
                final.write_bytes(r.content)
                log.info(f"✓ Exported: {final}")
                session.close()
                return final
        except: pass
        finally: session.close()
        
        log.info("[2/4] Google API...")
        if result := download_google_api(file_id, output): return result
        
        log.info("[3/4] Selenium...")
        if result := extract_sheets_selenium(url, file_id, output): return result
    
    # Google Docs
    elif is_google_docs(url) and file_id:
        log.info(">>> Google Docs")
        log.info("[1/2] Google API...")
        if result := download_google_api(file_id, output): return result
        
        log.info("[2/2] Direct export...")
        session = Session(proxy=proxy)
        for fmt in ['docx', 'pdf', 'odt']:
            try:
                r = session.get(f"https://docs.google.com/document/d/{file_id}/export?format={fmt}")
                if r and r.status_code == 200 and 'text/html' not in r.headers.get('content-type', ''):
                    final = output / f"{file_id[:8]}.{fmt}"
                    final.write_bytes(r.content)
                    log.info(f"✓ Exported as {fmt}: {final}")
                    session.close()
                    return final
            except: pass
        session.close()
    
    # Google Drive
    elif is_google_drive(url) and file_id:
        log.info(">>> Google Drive")
        log.info("[1/3] Google API...")
        if result := download_google_api(file_id, output): return result
        
        log.info("[2/3] UC export...")
        if result := download_google_drive_uc(file_id, output, proxy): return result
    
    # Direct
    log.info(">>> Direct download")
    return download_resume(url, output, proxy)

def main():
    print("\n" + "="*80)
    print("   ⚡ BYPASS DOWNLOADER – Universal Unrestricted File Downloader")
    print("   • Google Drive/Docs/Sheets (all restrictions bypassed)")
    print("   • Resume support • Stealth Selenium • Google API • Rate limiting")
    print("="*80 + "\n")
    
    try:
        url = input("📎 URL: ").strip()
        if not url:
            log.error("No URL")
            return
        
        output = input("📁 Output [cwd]: ").strip() or "."
        proxy = input("🌐 Proxy [none]: ").strip() or None
        
        log.info(f"URL: {url[:70]}...")
        log.info(f"Output: {Path(output).absolute()}")
        
        if result := download(url, Path(output), proxy):
            log.info(f"\n🎉 SUCCESS! File: {result}\n")
        else:
            log.error("\n❌ Failed\n")
            log.error("📦 Install: pip install -r requirements.txt")
            log.error("🔑 OAuth: Follow SETUP.md\n")
    
    except KeyboardInterrupt:
        log.warning("\nInterrupted")
    except Exception as e:
        log.error(f"Fatal: {e}")

if __name__ == "__main__":
    main()
