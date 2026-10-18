#!/usr/bin/env python3
"""
BYPASS DOWNLOADER - Universal Unrestricted File Downloader
Production-grade: Google Drive/Docs/Sheets, direct links, OAuth2
Complete rewrite: Enhanced stability, quality assurance, comprehensive auditing

Author: iamdev904590@gmail.com | License: MIT
Repo: https://github.com/DEVTHAKUR-90/bypass-downloader
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
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum
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

# ============= ENUMS & DATACLASSES =============
class URLType(Enum):
    """URL classification"""
    GOOGLE_SHEETS = "sheets"
    GOOGLE_DOCS = "docs"
    GOOGLE_DRIVE = "drive"
    DIRECT = "direct"
    UNKNOWN = "unknown"

@dataclass
class DownloadConfig:
    """Centralized configuration - fully optimized"""
    chunk_size: int = 4 * 1024 * 1024  # 4MB (increased for better performance)
    timeout_conn: int = 45              # Increased from 30
    timeout_read: int = 900             # Increased from 600
    max_retries: int = 10               # Increased from 7
    backoff_factor: float = 1.5         # Slightly reduced for faster retries
    min_file_size: int = 100
    rate_limit_delay: float = 1.2       # Slightly reduced
    rate_limit_jitter: float = 0.3
    cache_dir: Path = Path(".cache")
    selenium_timeout: int = 45
    selenium_sleep: int = 8
    verify_ssl: bool = True
    max_redirects: int = 10
    
    def __post_init__(self):
        self.cache_dir.mkdir(exist_ok=True)

# ============= LOGGING =============
class ColorFormatter(logging.Formatter):
    """ANSI color formatter for terminal output"""
    COLORS = {
        'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
        'ERROR': '\033[31m', 'CRITICAL': '\033[35m', 'RESET': '\033[0m',
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}[{record.levelname}]{self.COLORS['RESET']}"
        return super().format(record)

def setup_logger(name: str = "bypass") -> logging.Logger:
    """Initialize logger"""
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

log = setup_logger()

# ============= RESOURCE MANAGEMENT =============
class ResourceManager:
    """Centralized resource management - guaranteed cleanup"""
    _drivers: List = []
    _sessions: List = []
    
    @classmethod
    def add_driver(cls, driver):
        """Add driver for tracking"""
        cls._drivers.append(driver)
    
    @classmethod
    def remove_driver(cls, driver):
        """Remove driver from tracking"""
        if driver in cls._drivers:
            cls._drivers.remove(driver)
    
    @classmethod
    def add_session(cls, session):
        """Add session for tracking"""
        cls._sessions.append(session)
    
    @classmethod
    def remove_session(cls, session):
        """Remove session from tracking"""
        if session in cls._sessions:
            cls._sessions.remove(session)
    
    @classmethod
    def cleanup(cls):
        """Aggressive cleanup of ALL resources"""
        # Close drivers
        for driver in cls._drivers[:]:
            try:
                driver.quit()
            except Exception as e:
                log.debug(f"Driver quit error: {e}")
        cls._drivers.clear()
        
        # Close sessions
        for session in cls._sessions[:]:
            try:
                session.close()
            except Exception as e:
                log.debug(f"Session close error: {e}")
        cls._sessions.clear()
        
        log.debug("All resources cleaned up")

def _cleanup_handler():
    """Exit handler - ALWAYS runs"""
    ResourceManager.cleanup()

def _signal_handler(sig, frame):
    """Signal handler for SIGINT"""
    log.warning("\n❌ Interrupted by user")
    ResourceManager.cleanup()
    sys.exit(1)

atexit.register(_cleanup_handler)
signal.signal(signal.SIGINT, _signal_handler)

# ============= CONFIGURATION =============
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

# ============= VALIDATION =============
def validate_url(url: str) -> bool:
    """Validate URL structure"""
    try:
        parsed = urlparse(url)
        return all([parsed.scheme in ('http', 'https'), parsed.netloc])
    except Exception:
        return False

def validate_path(path: Path) -> bool:
    """Validate output path"""
    try:
        if path.exists():
            return path.is_dir() or path.parent.is_dir()
        parent = path if path.is_dir() else path.parent
        return parent.parent.exists() or parent.exists()
    except Exception:
        return False

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename).strip('._')
    # Limit length to 200 chars (filesystem safe)
    return filename[:200] if filename else "download"

def calculate_file_hash(filepath: Path, algorithm: str = 'md5') -> str:
    """Calculate file hash for validation"""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception:
        return ""

# ============= URL HELPERS =============
def identify_url_type(url: str) -> URLType:
    """Identify URL type"""
    if not url:
        return URLType.UNKNOWN
    
    url_lower = url.lower()
    if "docs.google.com/spreadsheets" in url_lower:
        return URLType.GOOGLE_SHEETS
    elif "docs.google.com/document" in url_lower:
        return URLType.GOOGLE_DOCS
    elif "drive.google.com" in url_lower or "docs.google.com" in url_lower:
        return URLType.GOOGLE_DRIVE
    elif url_lower.startswith(('http://', 'https://')):
        return URLType.DIRECT
    
    return URLType.UNKNOWN

def extract_file_id(url: str) -> Optional[str]:
    """Extract Google file ID from URL"""
    if not url:
        return None
    
    patterns = [
        r"/d/([a-zA-Z0-9_-]{20,})",
        r"[?&]id=([a-zA-Z0-9_-]{20,})",
        r"spreadsheets/d/([a-zA-Z0-9_-]{20,})",
        r"document/d/([a-zA-Z0-9_-]{20,})",
        r"presentation/d/([a-zA-Z0-9_-]{20,})",
    ]
    
    for pattern in patterns:
        try:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        except Exception:
            pass
    
    return None

# ============= SESSION MANAGEMENT =============
class HTTPSession:
    """Enhanced HTTP session with comprehensive error handling"""
    
    def __init__(self, config: DownloadConfig, proxy: Optional[str] = None):
        self.config = config
        self.proxy = proxy
        self.session = requests.Session()
        self.last_request_time = 0.0
        self.ua_index = 0
        self.cookies_file = config.cache_dir / "cookies.pkl"
        self.request_count = 0
        self.error_count = 0
        
        self._setup_session()
        self._load_cookies()
        ResourceManager.add_session(self.session)
    
    def _setup_session(self):
        """Configure session with optimal retry strategy"""
        retry_strategy = URLRetry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=15,
            pool_maxsize=15,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        if self.proxy:
            self.session.proxies.update({
                "http": self.proxy,
                "https": self.proxy,
            })
        
        self._update_headers()
    
    def _update_headers(self):
        """Rotate user agent and update headers"""
        ua = USER_AGENTS[self.ua_index % len(USER_AGENTS)]
        self.ua_index += 1
        
        self.session.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
    
    def _load_cookies(self):
        """Load cookies from cache"""
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.session.cookies.update(cookies)
                log.debug(f"Loaded {len(cookies)} cookies")
        except Exception as e:
            log.debug(f"Cookie load error: {e}")
            self.cookies_file.unlink(missing_ok=True)
    
    def _save_cookies(self):
        """Save cookies to cache"""
        try:
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(dict(self.session.cookies), f)
        except Exception as e:
            log.debug(f"Cookie save error: {e}")
    
    def _rate_limit(self):
        """Apply smart rate limiting"""
        elapsed = time.time() - self.last_request_time
        min_delay = self.config.rate_limit_delay
        
        if elapsed < min_delay:
            jitter = random.uniform(0, self.config.rate_limit_jitter)
            sleep_time = max(0, min_delay - elapsed + jitter)
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """GET request with rate limiting and error handling"""
        self._rate_limit()
        self._update_headers()
        self.request_count += 1
        
        try:
            timeout = kwargs.pop('timeout', (self.config.timeout_conn, self.config.timeout_read))
            response = self.session.get(
                url,
                timeout=timeout,
                verify=self.config.verify_ssl,
                allow_redirects=True,
                **kwargs
            )
            
            if response.status_code >= 400:
                self.error_count += 1
                log.debug(f"GET returned {response.status_code}")
            else:
                self._save_cookies()
            
            return response
        except requests.exceptions.Timeout:
            self.error_count += 1
            log.debug(f"GET timeout after {self.config.timeout_read}s")
            return None
        except requests.exceptions.ConnectionError:
            self.error_count += 1
            log.debug(f"GET connection error")
            return None
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            log.debug(f"GET error: {type(e).__name__}")
            return None
        except Exception as e:
            self.error_count += 1
            log.debug(f"GET unexpected error: {e}")
            return None
    
    def head(self, url: str, **kwargs) -> Optional[requests.Response]:
        """HEAD request"""
        self._update_headers()
        self.request_count += 1
        
        try:
            timeout = kwargs.pop('timeout', (self.config.timeout_conn, self.config.timeout_conn))
            return self.session.head(
                url,
                timeout=timeout,
                verify=self.config.verify_ssl,
                allow_redirects=True,
                **kwargs
            )
        except Exception as e:
            self.error_count += 1
            log.debug(f"HEAD error: {e}")
            return None
    
    def close(self):
        """Close session safely"""
        try:
            self.session.close()
            ResourceManager.remove_session(self.session)
            log.debug(f"Session closed (requests: {self.request_count}, errors: {self.error_count})")
        except Exception as e:
            log.debug(f"Session close error: {e}")

# ============= DOWNLOAD FUNCTIONS =============
class Downloader:
    """Main downloader with production-grade quality assurance"""
    
    def __init__(self, config: Optional[DownloadConfig] = None):
        self.config = config or DownloadConfig()
        self.download_stats = {
            'total_downloads': 0,
            'successful': 0,
            'failed': 0,
            'bytes_downloaded': 0,
        }
    
    def download_direct(self, url: str, output: Path, proxy: Optional[str] = None) -> Optional[Path]:
        """Download from direct HTTP(S) URL with resume and validation"""
        if not validate_url(url):
            log.error("❌ Invalid URL format")
            return None
        
        session = HTTPSession(self.config, proxy)
        
        try:
            log.info(f"🔍 Probing: {url[:50]}...")
            head_resp = session.head(url)
            
            if not head_resp or head_resp.status_code >= 400:
                log.error(f"❌ HEAD failed: HTTP {head_resp.status_code if head_resp else 'timeout'}")
                return None
            
            content_length = int(head_resp.headers.get('content-length', 0))
            supports_range = 'accept-ranges' in head_resp.headers.get('accept-ranges', '').lower()
            
            if content_length > 0:
                size_mb = content_length / (1024 ** 2)
                log.info(f"📊 Size: {size_mb:.2f}MB | Resume: {'✓' if supports_range else '✗'}")
            
            # Determine filename
            filename = self._extract_filename(url, head_resp)
            if not filename:
                filename = self._generate_filename(head_resp)
            
            final_path = output / filename if output.is_dir() else output
            
            # Check if resume is possible
            resume_mode = self._check_resume(final_path, content_length, supports_range)
            if resume_mode:
                existing_size = final_path.stat().st_size
                log.info(f"⏸️  Resuming: {existing_size}/{content_length} bytes")
                headers = {'Range': f'bytes={existing_size}-'}
                write_mode = 'ab'
            else:
                headers = {}
                write_mode = 'wb'
            
            # Download with progress
            get_resp = session.get(url, stream=True, headers=headers)
            if not get_resp or get_resp.status_code not in [200, 206]:
                log.error(f"❌ Download failed: HTTP {get_resp.status_code if get_resp else 'timeout'}")
                return None
            
            # Check for HTML error pages
            content_type = get_resp.headers.get('content-type', '').lower()
            if 'text/html' in content_type or 'text/plain' in content_type:
                log.error("❌ Received error page (blocked or wrong URL)")
                return None
            
            # Write file with comprehensive tracking
            bytes_written = 0 if write_mode == 'wb' else final_path.stat().st_size
            last_log_bytes = 0
            chunks_written = 0
            
            try:
                with open(final_path, write_mode) as f:
                    for chunk in get_resp.iter_content(chunk_size=self.config.chunk_size):
                        if chunk:
                            f.write(chunk)
                            bytes_written += len(chunk)
                            chunks_written += 1
                            self.download_stats['bytes_downloaded'] += len(chunk)
                            
                            if content_length > 0 and bytes_written - last_log_bytes > 100 * self.config.chunk_size:
                                progress = (bytes_written / content_length) * 100
                                log.info(f"📈 Progress: {progress:.1f}% ({bytes_written / (1024**2):.2f}MB/{content_length / (1024**2):.2f}MB)")
                                last_log_bytes = bytes_written
            except IOError as e:
                log.error(f"❌ Write error: {e}")
                return None
            except Exception as e:
                log.error(f"❌ Download interrupted: {e}")
                return None
            
            # Validate final file
            if not self._validate_file(final_path):
                return None
            
            self.download_stats['successful'] += 1
            log.info(f"✅ Downloaded: {final_path} ({chunks_written} chunks)")
            return final_path
        
        except Exception as e:
            self.download_stats['failed'] += 1
            log.error(f"❌ Download error: {e}")
            log.debug(traceback.format_exc())
            return None
        finally:
            session.close()
    
    def download_google_api(self, file_id: str, output: Path) -> Optional[Path]:
        """Download using Google Drive API with quality checks"""
        if not GOOGLE_API_AVAILABLE:
            log.debug("Google API not available")
            return None
        
        try:
            log.info("🔗 Attempting Google API download...")
            
            creds = self._get_google_credentials()
            if not creds:
                log.debug("No valid credentials")
                return None
            
            service = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            file_meta = service.files().get(
                fileId=file_id,
                fields='name, mimeType, size'
            ).execute()
            
            filename = file_meta.get('name', f'file_{file_id[:8]}')
            mime_type = file_meta.get('mimeType', '')
            file_size = file_meta.get('size', 0)
            
            # Handle Google Docs
            if 'vnd.google-apps' in mime_type:
                filename, export_mime = self._get_export_format(filename, mime_type)
                if not export_mime:
                    log.warning(f"❌ Unsupported doc type: {mime_type}")
                    return None
                
                request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                request = service.files().get_media(fileId=file_id)
            
            final_path = output / filename if output.is_dir() else output
            
            log.info(f"💾 Downloading {filename} via API...")
            
            with open(final_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=self.config.chunk_size)
                done = False
                chunks = 0
                
                while not done:
                    try:
                        status, done = downloader.next_chunk()
                        if status:
                            chunks += 1
                            progress = int(status.progress() * 100)
                            if progress % 25 == 0:  # Log every 25%
                                log.info(f"📈 API: {progress}%")
                    except HttpError as e:
                        log.error(f"❌ API error: {e}")
                        return None
            
            if not self._validate_file(final_path):
                return None
            
            self.download_stats['successful'] += 1
            log.info(f"✅ API download: {final_path} ({chunks} chunks)")
            return final_path
        
        except Exception as e:
            self.download_stats['failed'] += 1
            log.debug(f"API failed: {e}")
            return None
    
    def download_google_drive_uc(self, file_id: str, output: Path, proxy: Optional[str] = None) -> Optional[Path]:
        """Download Google Drive via UC export"""
        session = HTTPSession(self.config, proxy)
        
        try:
            log.info("🔓 Trying UC export...")
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            resp = session.get(url)
            if not resp:
                return None
            
            # Check for confirmation cookie
            for cookie_name, cookie_value in resp.cookies.items():
                if 'download' in cookie_name.lower():
                    resp = session.get(f"{url}&confirm={cookie_value}", stream=True)
                    break
            
            if not resp or 'text/html' in resp.headers.get('content-type', ''):
                log.debug("UC export blocked")
                return None
            
            filename = self._extract_filename_from_header(resp.headers.get('content-disposition', ''))
            if not filename:
                filename = f"gdrive_{file_id[:8]}"
            
            final_path = output / filename if output.is_dir() else output
            
            bytes_written = 0
            chunks = 0
            
            with open(final_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=self.config.chunk_size):
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
                        chunks += 1
            
            if not self._validate_file(final_path):
                return None
            
            self.download_stats['successful'] += 1
            log.info(f"✅ UC export: {final_path} ({chunks} chunks)")
            return final_path
        
        except Exception as e:
            self.download_stats['failed'] += 1
            log.debug(f"UC failed: {e}")
            return None
        finally:
            session.close()
    
    def extract_sheets_selenium(self, url: str, file_id: str, output: Path) -> Optional[Path]:
        """Extract Google Sheets with stability improvements"""
        if not SELENIUM_AVAILABLE or not PANDAS_AVAILABLE or not OPENPYXL_AVAILABLE:
            log.debug("Selenium/pandas/openpyxl not available")
            return None
        
        driver = None
        
        try:
            log.info("🤖 Starting Selenium...")
            
            driver = self._create_selenium_driver()
            if not driver:
                return None
            
            ResourceManager.add_driver(driver)
            
            driver.set_page_load_timeout(self.config.selenium_timeout)
            driver.get(f"https://docs.google.com/spreadsheets/d/{file_id}/edit")
            time.sleep(self.config.selenium_sleep)
            
            sheets = self._extract_sheet_names(driver)
            if not sheets:
                sheets = ["Sheet1"]
            
            log.info(f"📄 Found {len(sheets)} sheets: {sheets}")
            
            sheets_data = {}
            for sheet_name in sheets:
                try:
                    log.info(f"  Extracting: {sheet_name}")
                    data = self._extract_sheet_data(driver, sheet_name)
                    if data and len(data) > 0:
                        sheets_data[sheet_name] = data
                        log.info(f"    ✓ {len(data)} rows")
                    else:
                        log.warning(f"    ✗ No data")
                except Exception as e:
                    log.warning(f"    Error: {e}")
            
            if not sheets_data:
                log.error("❌ No sheets data extracted")
                return None
            
            try:
                excel_file = output / f"{file_id[:8]}.xlsx"
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    for sheet_name, data in sheets_data.items():
                        try:
                            if len(data) > 1:
                                df = pd.DataFrame(data[1:], columns=data[0])
                            else:
                                df = pd.DataFrame(data)
                            
                            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                        except Exception as e:
                            log.warning(f"Write error for {sheet_name}: {e}")
                
                if not self._validate_file(excel_file):
                    return None
                
                self.download_stats['successful'] += 1
                log.info(f"✅ Extracted to {excel_file}")
                return excel_file
            
            except Exception as e:
                log.error(f"❌ Excel export failed: {e}")
                return None
        
        except Exception as e:
            self.download_stats['failed'] += 1
            log.error(f"❌ Selenium extraction failed: {e}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                    ResourceManager.remove_driver(driver)
                except Exception:
                    pass
    
    # ============= HELPER METHODS =============
    def _create_selenium_driver(self):
        """Create Selenium driver with fallback"""
        try:
            chrome_opts = ChromeOptions()
            for arg in [
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
            ]:
                chrome_opts.add_argument(arg)
            
            chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_opts.add_experimental_option("useAutomationExtension", False)
            chrome_opts.add_argument("--user-data-dir=/tmp/chrome_data")
            
            driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=chrome_opts
            )
            log.debug("✓ Chrome driver created")
            return driver
        
        except Exception as e:
            log.debug(f"Chrome failed: {e}, trying Firefox...")
            try:
                firefox_opts = FirefoxOptions()
                firefox_opts.add_argument("--headless")
                firefox_opts.add_argument("--no-sandbox")
                
                driver = webdriver.Firefox(
                    service=webdriver.firefox.service.Service(GeckoDriverManager().install()),
                    options=firefox_opts
                )
                log.debug("✓ Firefox driver created")
                return driver
            except Exception as e:
                log.debug(f"Firefox failed: {e}")
                return None
    
    def _extract_sheet_names(self, driver) -> List[str]:
        """Extract sheet tab names safely"""
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@role='tab']"))
            )
            
            sheets = []
            for tab in driver.find_elements(By.XPATH, "//div[@role='tab']"):
                try:
                    name = tab.text.strip()
                    if name and len(name) < 100 and name not in sheets:
                        sheets.append(name)
                except (StaleElementReferenceException, NoSuchElementException):
                    pass
            
            return sheets if sheets else ["Sheet1"]
        except TimeoutException:
            return ["Sheet1"]
        except Exception as e:
            log.debug(f"Sheet extraction error: {e}")
            return []
    
    def _extract_sheet_data(self, driver, sheet_name: str):
        """Extract data from sheet"""
        try:
            driver.execute_script(f"""
            for (var tab of document.querySelectorAll('div[role="tab"]')) {{
                if (tab.innerText.trim() === {json.dumps(sheet_name)}) {{
                    tab.click();
                    break;
                }}
            }}
            """)
            time.sleep(3)
            
            data = driver.execute_script("""
            var cells = document.querySelectorAll('[role="gridcell"]');
            var map = {}, rows = {};
            
            cells.forEach(cell => {
                try {
                    var rect = cell.getBoundingClientRect();
                    var key = Math.round(rect.top) + "," + Math.round(rect.left);
                    map[key] = (cell.innerText || '').substring(0, 1000);
                } catch (e) {}
            });
            
            for (var key in map) {
                var [y, x] = key.split(",");
                if (!rows[y]) rows[y] = {};
                rows[y][x] = map[key];
            }
            
            var result = [];
            Object.keys(rows).sort((a, b) => a - b).forEach(y => {
                var cols = [];
                Object.keys(rows[y]).sort((a, b) => a - b).forEach(x => {
                    cols.push(rows[y][x]);
                });
                result.push(cols);
            });
            
            return result.slice(0, 10000);
            """)
            
            return data if data and len(data) > 0 else None
        
        except Exception as e:
            log.debug(f"Data extraction error: {e}")
            return None
    
    def _get_google_credentials(self):
        """Get or refresh Google credentials"""
        try:
            token_file = self.config.cache_dir / "token.json"
            creds_file = Path("credentials.json")
            
            if token_file.exists():
                try:
                    creds = Credentials.from_authorized_user_file(token_file)
                    if creds.valid:
                        return creds
                except Exception:
                    token_file.unlink(missing_ok=True)
            
            if token_file.exists():
                try:
                    creds = Credentials.from_authorized_user_file(token_file)
                    if creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        return creds
                except Exception:
                    token_file.unlink(missing_ok=True)
            
            if creds_file.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        creds_file,
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                    creds = flow.run_local_server(port=0, open_browser=True)
                    
                    with open(token_file, 'w') as f:
                        f.write(creds.to_json())
                    
                    return creds
                except Exception as e:
                    log.debug(f"OAuth failed: {e}")
            
            return None
        
        except Exception as e:
            log.debug(f"Credentials error: {e}")
            return None
    
    def _get_export_format(self, filename: str, mime_type: str) -> Tuple[str, Optional[str]]:
        """Get export format for Google Docs"""
        stem = Path(filename).stem
        
        exports = {
            'vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
            'vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
            'vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
        }
        
        for key, (export_mime, ext) in exports.items():
            if key in mime_type:
                return stem + ext, export_mime
        
        return filename, None
    
    def _extract_filename(self, url: str, response) -> Optional[str]:
        """Extract filename from URL or headers"""
        content_disp = response.headers.get('content-disposition', '')
        if content_disp:
            filename = self._extract_filename_from_header(content_disp)
            if filename:
                return filename
        
        url_part = url.split('/')[-1].split('?')[0]
        if url_part and '.' in url_part:
            return sanitize_filename(url_part)
        
        return None
    
    def _extract_filename_from_header(self, header: str) -> Optional[str]:
        """Extract filename from Content-Disposition header"""
        try:
            parts = header.split('filename=')
            if len(parts) > 1:
                filename = parts[-1].strip('"\'')
                return sanitize_filename(filename) if filename else None
        except Exception:
            pass
        return None
    
    def _generate_filename(self, response) -> str:
        """Generate filename from content type"""
        content_type = response.headers.get('content-type', '').split(';')[0].lower()
        
        extensions = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/zip': 'zip',
            'text/plain': 'txt',
            'text/html': 'html',
            'application/json': 'json',
            'image/jpeg': 'jpg',
            'image/png': 'png',
        }
        
        ext = next((extensions[ct] for ct in extensions if ct in content_type), 'bin')
        return f"download_{int(time.time())}.{ext}"
    
    def _check_resume(self, filepath: Path, total_size: int, supports_range: bool) -> bool:
        """Check if resume is possible"""
        if not filepath.exists():
            return False
        
        if not supports_range:
            return False
        
        current_size = filepath.stat().st_size
        return 0 < current_size < total_size
    
    def _validate_file(self, filepath: Path) -> bool:
        """Comprehensive file validation"""
        try:
            if not filepath.exists():
                log.error("File not found")
                return False
            
            file_size = filepath.stat().st_size
            if file_size < self.config.min_file_size:
                log.error(f"File too small ({file_size}B, min {self.config.min_file_size}B)")
                filepath.unlink()
                return False
            
            # Check if file is readable
            with open(filepath, 'rb') as f:
                first_bytes = f.read(100)
                if not first_bytes:
                    log.error("File is empty")
                    filepath.unlink()
                    return False
            
            log.debug(f"✓ File validated: {file_size}B")
            return True
        except Exception as e:
            log.error(f"Validation error: {e}")
            return False
    
    def download(self, url: str, output: Optional[Path] = None, proxy: Optional[str] = None) -> Optional[Path]:
        """Main download with comprehensive fallback strategy"""
        if not validate_url(url):
            log.error("❌ Invalid URL")
            return None
        
        if output is None:
            output = Path.cwd()
        
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"❌ Cannot create directory: {e}")
            return None
        
        if not validate_path(output):
            log.error("❌ Invalid output path")
            return None
        
        self.download_stats['total_downloads'] += 1
        url_type = identify_url_type(url)
        file_id = extract_file_id(url) if url_type != URLType.DIRECT else None
        
        try:
            if url_type == URLType.GOOGLE_SHEETS and file_id:
                log.info(">>> 📊 Google Sheets detected")
                
                log.info("[1/4] Direct XLSX export...")
                session = HTTPSession(self.config, proxy)
                try:
                    resp = session.get(f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx")
                    if resp and resp.status_code == 200 and 'text/html' not in resp.headers.get('content-type', ''):
                        final = output / f"{file_id[:8]}.xlsx"
                        final.write_bytes(resp.content)
                        if self._validate_file(final):
                            self.download_stats['successful'] += 1
                            log.info(f"✅ Direct export: {final}")
                            return final
                except Exception as e:
                    log.debug(f"Direct export failed: {e}")
                finally:
                    session.close()
                
                log.info("[2/4] Google API...")
                if result := self.download_google_api(file_id, output):
                    return result
                
                log.info("[3/4] Selenium extraction...")
                if result := self.extract_sheets_selenium(url, file_id, output):
                    return result
                
                log.error("❌ All Sheets methods failed")
                self.download_stats['failed'] += 1
                return None
            
            elif url_type == URLType.GOOGLE_DOCS and file_id:
                log.info(">>> 📄 Google Docs detected")
                
                log.info("[1/2] Google API...")
                if result := self.download_google_api(file_id, output):
                    return result
                
                log.info("[2/2] Direct export...")
                session = HTTPSession(self.config, proxy)
                try:
                    for fmt in ['docx', 'pdf', 'odt']:
                        resp = session.get(f"https://docs.google.com/document/d/{file_id}/export?format={fmt}")
                        if resp and resp.status_code == 200 and 'text/html' not in resp.headers.get('content-type', ''):
                            final = output / f"{file_id[:8]}.{fmt}"
                            final.write_bytes(resp.content)
                            if self._validate_file(final):
                                self.download_stats['successful'] += 1
                                log.info(f"✅ Direct export ({fmt}): {final}")
                                return final
                except Exception as e:
                    log.debug(f"Direct export failed: {e}")
                finally:
                    session.close()
                
                log.error("❌ All Docs methods failed")
                self.download_stats['failed'] += 1
                return None
            
            elif url_type == URLType.GOOGLE_DRIVE and file_id:
                log.info(">>> 🔗 Google Drive detected")
                
                log.info("[1/3] Google API...")
                if result := self.download_google_api(file_id, output):
                    return result
                
                log.info("[2/3] UC export...")
                if result := self.download_google_drive_uc(file_id, output, proxy):
                    return result
                
                log.error("❌ All Drive methods failed")
                self.download_stats['failed'] += 1
                return None
            
            else:
                log.info(">>> 📥 Direct download")
                return self.download_direct(url, output, proxy)
        
        except Exception as e:
            self.download_stats['failed'] += 1
            log.error(f"❌ Download error: {e}")
            log.debug(traceback.format_exc())
            return None

# ============= CLI =============
def main():
    """Interactive CLI"""
    print("\n" + "="*80)
    print("   ⚡ BYPASS DOWNLOADER – Universal Unrestricted File Downloader v2.1")
    print("   • Google Drive/Docs/Sheets • Resume support • Stealth Selenium • OAuth2")
    print("   • Enhanced stability • Quality assurance • Comprehensive error handling")
    print("="*80 + "\n")
    
    try:
        url = input("📎 URL: ").strip()
        if not url:
            log.error("No URL provided")
            return
        
        output = input("📁 Output [cwd]: ").strip() or "."
        proxy = input("🌐 Proxy [none]: ").strip() or None
        
        log.info(f"URL: {url[:70]}...")
        log.info(f"Output: {Path(output).absolute()}")
        
        downloader = Downloader()
        result = downloader.download(url, Path(output), proxy)
        
        if result:
            log.info(f"\n🎉 SUCCESS! File: {result}")
            log.info(f"Stats: {downloader.download_stats}\n")
        else:
            log.error("\n❌ Download failed")
            log.error("📦 Install: pip install -r requirements.txt")
            log.error("🔑 Setup: Follow SETUP.md\n")
    
    except KeyboardInterrupt:
        log.warning("❌ Interrupted")
    except Exception as e:
        log.error(f"Fatal: {e}")
        log.debug(traceback.format_exc())

if __name__ == "__main__":
    main()
