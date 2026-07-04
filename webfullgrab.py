# ============================================================
# File: ultimate_web_downloader.py
# Author: github.com/Mikaeil297
# Version: 3.0 (Ultimate Edition with Real Database Support)
# Description: Full webpage downloader with 15 advanced features
#              and REAL database connection capability.
# ============================================================

import os
import re
import json
import requests
import concurrent.futures
import shutil
import time
import base64
import sys
import mimetypes
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

# Optional imports for advanced features
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    import ftplib
    FTP_AVAILABLE = True
except ImportError:
    FTP_AVAILABLE = False

# Initialize colorama
init(autoreset=True)


# ============================================================
# Configuration & Settings
# ============================================================

class Settings:
    """Load and save settings from/to a JSON config file."""
    def __init__(self, config_file='settings.json'):
        self.config_file = config_file
        self.defaults = {
            'max_workers': 5,
            'max_depth': 3,
            'retries': 3,
            'timeout': 15,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'proxy': None,
            'include_patterns': [],
            'exclude_patterns': [],
            'batch_mode': False,
            'auto_yes': False,
            'save_single_file': False,
            'cleanup': True,
            'generate_sitemap': True,
            'use_selenium': False,
            'cookies_file': None,
            'download_fonts': True,
            'download_media': True,
            'download_data': True,
            'follow_ftp': False,
        }
        self.data = {}
        self.load()

    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
            for key, value in self.defaults.items():
                if key not in self.data:
                    self.data[key] = value
        except FileNotFoundError:
            self.data = self.defaults.copy()
            self.save()

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


settings = Settings()


# ============================================================
# Download State for Resume
# ============================================================

download_state = {
    'completed_files': {},
    'visited_urls': set(),
    'sitemap': [],
}


def save_download_state(folder):
    state_file = os.path.join(folder, '.download_state.json')
    try:
        state = {
            'completed_files': download_state['completed_files'],
            'visited_urls': list(download_state['visited_urls']),
            'sitemap': download_state['sitemap'],
            'timestamp': time.time()
        }
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"{Fore.RED}⚠️  Failed to save state: {e}")


def load_download_state(folder):
    state_file = os.path.join(folder, '.download_state.json')
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        download_state['completed_files'] = state.get('completed_files', {})
        download_state['visited_urls'] = set(state.get('visited_urls', []))
        download_state['sitemap'] = state.get('sitemap', [])
        print(f"{Fore.GREEN}✅  Loaded download state (resume mode)")
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"{Fore.RED}⚠️  Failed to load state: {e}")
        return False


# ============================================================
# Core Helper Functions
# ============================================================

def create_folder_from_url(url):
    try:
        parsed = urlparse(url)
        folder_name = parsed.netloc.replace("www.", "").split(".")[0]
        if not folder_name:
            folder_name = "downloaded_page"
        os.makedirs(folder_name, exist_ok=True)
        return folder_name
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error creating folder: {e}")
        return "downloaded_page"


def get_absolute_url(base_url, link):
    try:
        return urljoin(base_url, link)
    except Exception:
        return link


def get_session():
    session = requests.Session()
    session.headers.update({'User-Agent': settings.get('user_agent')})
    proxy = settings.get('proxy')
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}
    cookies_file = settings.get('cookies_file')
    if cookies_file and os.path.exists(cookies_file):
        try:
            import http.cookiejar as cookielib
            cj = cookielib.MozillaCookieJar(cookies_file)
            cj.load()
            session.cookies = cj
            print(f"{Fore.GREEN}✅  Cookies loaded from {cookies_file}")
        except Exception as e:
            print(f"{Fore.RED}⚠️  Failed to load cookies: {e}")
    return session


def download_file(url, save_path, retries=None, session=None):
    if retries is None:
        retries = settings.get('retries', 3)
    if session is None:
        session = get_session()

    if url in download_state['completed_files']:
        print(f"{Fore.CYAN}⏭️  Already downloaded: {os.path.basename(save_path)}")
        return True, None

    for attempt in range(retries):
        try:
            response = session.get(url, timeout=settings.get('timeout', 15))
            response.raise_for_status()
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(response.content)
            download_state['completed_files'][url] = {
                'path': save_path,
                'size': len(response.content),
                'timestamp': time.time()
            }
            content_type = response.headers.get('content-type', '')
            if any(t in content_type for t in ['text', 'javascript', 'css']):
                return True, response.text
            return True, None
        except requests.exceptions.Timeout:
            print(f"{Fore.RED}⏱️  Timeout (attempt {attempt+1}/{retries})")
        except requests.exceptions.HTTPError as e:
            print(f"{Fore.RED}❌  HTTP {e.response.status_code}")
            break
        except Exception as e:
            print(f"{Fore.RED}💥  Error: {e}")
        time.sleep(1)
    return False, None


# ============================================================
# Extract Resources (CSS, JS, Images, Fonts, Media, Data, PHP)
# ============================================================

def extract_inline_resources(soup, resource_type):
    contents = []
    try:
        if resource_type == 'css':
            for tag in soup.find_all('style'):
                if tag.string:
                    contents.append(tag.string.strip())
        elif resource_type == 'js':
            for tag in soup.find_all('script', src=False):
                if tag.string:
                    contents.append(tag.string.strip())
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting inline {resource_type}: {e}")
    return contents


def extract_external_resources(soup, base_url, resource_type):
    resources = []
    try:
        if resource_type == 'css':
            for tag in soup.find_all('link', rel='stylesheet'):
                href = tag.get('href')
                if href:
                    resources.append(get_absolute_url(base_url, href))
        elif resource_type == 'js':
            for tag in soup.find_all('script', src=True):
                src = tag.get('src')
                if src:
                    resources.append(get_absolute_url(base_url, src))
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting external {resource_type}: {e}")
    return resources


def extract_images_from_html(soup, base_url):
    image_urls = set()
    try:
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                image_urls.add(get_absolute_url(base_url, src))
            srcset = img.get('srcset')
            if srcset:
                for part in srcset.split(','):
                    part = part.strip().split(' ')[0]
                    if part:
                        image_urls.add(get_absolute_url(base_url, part))
            for attr in ['data-src', 'data-original']:
                val = img.get(attr)
                if val:
                    image_urls.add(get_absolute_url(base_url, val))
        for tag in soup.find_all(style=True):
            urls = re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', tag['style'])
            for u in urls:
                image_urls.add(get_absolute_url(base_url, u))
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting images: {e}")
    return image_urls


def extract_fonts(soup, base_url):
    fonts = set()
    try:
        for style in soup.find_all('style'):
            if style.string:
                urls = re.findall(r'url\([\'"]?([^\'")]+\.(woff2?|ttf|otf|eot)[^\'")]*)[\'"]?\)', style.string)
                for url in urls:
                    fonts.add(get_absolute_url(base_url, url[0] if isinstance(url, tuple) else url))
        for link in soup.find_all('link', rel='preload'):
            if link.get('as') == 'font':
                href = link.get('href')
                if href:
                    fonts.add(get_absolute_url(base_url, href))
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting fonts: {e}")
    return fonts


def extract_media(soup, base_url):
    media = set()
    try:
        for tag in soup.find_all(['video', 'audio']):
            src = tag.get('src')
            if src:
                media.add(get_absolute_url(base_url, src))
            for source in tag.find_all('source'):
                src = source.get('src')
                if src:
                    media.add(get_absolute_url(base_url, src))
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and src.lower().endswith('.svg'):
                media.add(get_absolute_url(base_url, src))
        for tag in soup.find_all(['object', 'embed']):
            data = tag.get('data') or tag.get('src')
            if data:
                media.add(get_absolute_url(base_url, data))
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting media: {e}")
    return media


def extract_data_files(soup, base_url):
    data_files = set()
    try:
        for script in soup.find_all('script', src=True):
            src = script['src']
            if src and any(src.lower().endswith(ext) for ext in ['.json', '.xml']):
                data_files.add(get_absolute_url(base_url, src))
        for link in soup.find_all('link'):
            href = link.get('href')
            if href and any(href.lower().endswith(ext) for ext in ['.json', '.xml', '.rss', '.atom']):
                data_files.add(get_absolute_url(base_url, href))
        for script in soup.find_all('script'):
            if script.string:
                urls = re.findall(r'["\'](/[^"\']+\.(json|xml))["\']', script.string)
                for url in urls:
                    if url:
                        data_files.add(get_absolute_url(base_url, url[0] if isinstance(url, tuple) else url))
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting data files: {e}")
    return data_files


def extract_php_files(soup, base_url):
    php_extensions = ('.php', '.asp', '.aspx', '.jsp', '.do')
    urls = set()
    for tag in soup.find_all(['a', 'link', 'script', 'img', 'form']):
        attr_map = {'form': 'action', 'link': 'href', 'script': 'src', 'img': 'src', 'a': 'href'}
        attr = attr_map.get(tag.name)
        if attr:
            val = tag.get(attr)
            if val:
                abs_url = get_absolute_url(base_url, val)
                if urlparse(abs_url).path.lower().endswith(php_extensions):
                    urls.add(abs_url)
    return urls


def extract_external_links(soup, base_url):
    external = set()
    try:
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            abs_url = get_absolute_url(base_url, href)
            parsed = urlparse(abs_url)
            if parsed.netloc and parsed.netloc != base_domain:
                external.add(abs_url)
    except Exception as e:
        print(f"{Fore.RED}⚠️  Error extracting external links: {e}")
    return external


# ============================================================
# Download Functions (Parallel, Images, FTP)
# ============================================================

def download_resources_parallel(urls, base_url, folder, resource_type, download_func, **kwargs):
    if not urls:
        return {}
    max_workers = settings.get('max_workers', 5)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(download_func, url, base_url, folder, **kwargs): url
            for url in urls
        }
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                if result:
                    results[url] = result
            except Exception as e:
                print(f"{Fore.RED}✖  Error downloading {url}: {e}")
    return results


def download_image(url, base_url, folder, image_map, images_folder='images'):
    if not url:
        return None
    absolute_url = get_absolute_url(base_url, url)
    parsed = urlparse(absolute_url)
    filename = os.path.basename(parsed.path) or f"image_{len(image_map)+1}.jpg"
    filename = unquote(filename)
    if absolute_url in image_map:
        return image_map[absolute_url]
    images_path = os.path.join(folder, images_folder)
    os.makedirs(images_path, exist_ok=True)
    base, ext = os.path.splitext(filename)
    counter = 1
    final_filename = filename
    save_path = os.path.join(images_path, final_filename)
    while os.path.exists(save_path):
        final_filename = f"{base}_{counter}{ext}"
        save_path = os.path.join(images_path, final_filename)
        counter += 1
    success, _ = download_file(absolute_url, save_path)
    if success:
        image_map[absolute_url] = final_filename
        print(f"{Fore.GREEN}   🖼️  Downloaded: {final_filename}")
        return final_filename
    return None


def download_ftp(url, save_path, session=None):
    if not FTP_AVAILABLE:
        print(f"{Fore.RED}❌  ftplib not available")
        return False, None
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        path = parsed.path
        if parsed.port:
            ftp = ftplib.FTP()
            ftp.connect(host, parsed.port)
        else:
            ftp = ftplib.FTP(host)
        ftp.login()
        with open(save_path, 'wb') as f:
            ftp.retrbinary(f'RETR {path}', f.write)
        ftp.quit()
        return True, None
    except Exception as e:
        print(f"{Fore.RED}❌  FTP error: {e}")
        return False, None


# ============================================================
# CSS/JS Processing
# ============================================================

def process_css_images(css_content, base_url, folder, image_map):
    pattern = r'url\([\'"]?([^\'")]+)[\'"]?\)'
    matches = re.findall(pattern, css_content)
    for url in matches:
        absolute_url = get_absolute_url(base_url, url)
        local_name = download_image(absolute_url, base_url, folder, image_map)
        if local_name:
            css_content = css_content.replace(url, f"images/{local_name}")
    return css_content


def process_css_imports(css_content, css_url, base_url, folder, visited_imports, image_map):
    css_content = process_css_images(css_content, base_url, folder, image_map)
    import_pattern = r'@import\s+url\([\'"]?([^\'")]+)[\'"]?\)|@import\s+[\'"]([^\'"]+)[\'"]'
    imports = re.findall(import_pattern, css_content)
    for url_tuple in imports:
        import_url = url_tuple[0] or url_tuple[1]
        if not import_url:
            continue
        absolute_url = get_absolute_url(base_url, import_url)
        if absolute_url in visited_imports:
            continue
        visited_imports.add(absolute_url)
        filename = os.path.basename(urlparse(absolute_url).path) or f"import_{len(visited_imports)}.css"
        save_path = os.path.join(folder, filename)
        success, content = download_file(absolute_url, save_path)
        if success and content:
            content = process_css_imports(content, absolute_url, base_url, folder, visited_imports, image_map)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            css_content = css_content.replace(import_url, filename)
    return css_content


def process_js_imports(js_content, js_url, base_url, folder, visited_imports):
    static_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
    dynamic_pattern = r'import\s*\([\'"]([^\'"]+)[\'"]\)'
    all_matches = re.findall(static_pattern, js_content) + re.findall(dynamic_pattern, js_content)
    for import_path in set(all_matches):
        if not import_path:
            continue
        absolute_url = get_absolute_url(base_url, import_path)
        if absolute_url in visited_imports:
            continue
        visited_imports.add(absolute_url)
        filename = os.path.basename(urlparse(absolute_url).path) or f"import_{len(visited_imports)}.js"
        save_path = os.path.join(folder, filename)
        success, content = download_file(absolute_url, save_path)
        if success and content:
            content = process_js_imports(content, absolute_url, base_url, folder, visited_imports)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            js_content = js_content.replace(import_path, filename)
    return js_content


# ============================================================
# Update HTML References
# ============================================================

def update_html_references(html_content, resource_map, image_map, php_map, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup.find_all('link', rel='stylesheet'):
        href = tag.get('href')
        if href:
            for orig_url, local_name in resource_map.get('css', []):
                if href == orig_url or href.endswith(orig_url):
                    tag['href'] = local_name
                    break

    for tag in soup.find_all('script', src=True):
        src = tag.get('src')
        if src:
            for orig_url, local_name in resource_map.get('js', []):
                if src == orig_url or src.endswith(orig_url):
                    tag['src'] = local_name
                    break

    def find_local_image(url):
        if not url:
            return None
        abs_url = get_absolute_url(base_url, url)
        if abs_url in image_map:
            return image_map[abs_url]
        for orig_url, lname in image_map.items():
            if orig_url.endswith(abs_url) or abs_url.endswith(orig_url):
                return lname
        return None

    def find_local_php(url):
        if not url:
            return None
        abs_url = get_absolute_url(base_url, url)
        if abs_url in php_map:
            return php_map[abs_url]
        for orig_url, lname in php_map.items():
            if orig_url.endswith(abs_url) or abs_url.endswith(orig_url):
                return lname
        return None

    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            local = find_local_image(src)
            if local:
                img['src'] = 'images/' + local
        srcset = img.get('srcset')
        if srcset:
            new_parts = []
            for part in srcset.split(','):
                part = part.strip()
                if not part:
                    continue
                pieces = part.split()
                if pieces:
                    url_part = pieces[0]
                    local = find_local_image(url_part)
                    if local:
                        new_part = 'images/' + local
                        if len(pieces) > 1:
                            new_part += ' ' + ' '.join(pieces[1:])
                        new_parts.append(new_part)
                    else:
                        new_parts.append(part)
            if new_parts:
                img['srcset'] = ', '.join(new_parts)

    for tag in soup.find_all(['a', 'link', 'script', 'img', 'form']):
        attr_map = {'form': 'action', 'link': 'href', 'script': 'src', 'img': 'src', 'a': 'href'}
        attr = attr_map.get(tag.name)
        if attr:
            val = tag.get(attr)
            if val:
                local = find_local_php(val)
                if local:
                    tag[attr] = local

    return str(soup)


# ============================================================
# Database Real Connection Functions
# ============================================================

def extract_db_variables(php_content):
    db_vars = {}
    try:
        patterns = {
            r'\$(db_)?host\s*=\s*(["\'])([^"\']+)\2': 'DB_HOST',
            r'\$(db_)?(user|username)\s*=\s*(["\'])([^"\']+)\4': 'DB_USER',
            r'\$(db_)?(pass|password)\s*=\s*(["\'])([^"\']+)\6': 'DB_PASS',
            r'\$(db_)?(name|dbname|database)\s*=\s*(["\'])([^"\']+)\8': 'DB_NAME',
        }
        for pattern, const_name in patterns.items():
            matches = re.findall(pattern, php_content)
            for match in matches:
                value = match[-1]
                var_name = match[0] if match[0] else None
                if var_name and value:
                    db_vars[var_name] = value
                elif value:
                    db_vars[const_name] = value
    except Exception as e:
        print(f"{Fore.RED}⚠️  DB var extraction error: {e}")
    return db_vars


def get_db_credentials_from_user():
    print(f"{Fore.YELLOW}🐘  DATABASE CONFIGURATION (REAL CONNECTION)")
    print(f"{Fore.CYAN}ℹ️  You need a local or remote database server.")
    print(f"{Fore.CYAN}ℹ️  For local: install XAMPP, WAMP, or use Termux with MySQL.")
    print("")
    creds = {}
    creds['host'] = input(f"{Fore.GREEN}📌  Database Host (e.g., localhost): {Style.RESET_ALL}").strip()
    if not creds['host']:
        creds['host'] = 'localhost'
    creds['user'] = input(f"{Fore.GREEN}👤  Database Username: {Style.RESET_ALL}").strip()
    if not creds['user']:
        creds['user'] = 'root'
    creds['password'] = input(f"{Fore.GREEN}🔑  Database Password (leave empty if none): {Style.RESET_ALL}").strip()
    creds['dbname'] = input(f"{Fore.GREEN}📊  Database Name (e.g., website_db): {Style.RESET_ALL}").strip()
    if not creds['dbname']:
        creds['dbname'] = 'test'
    print(f"{Fore.CYAN}\n📋  Configuration:")
    print(f"   Host: {creds['host']}")
    print(f"   User: {creds['user']}")
    print(f"   Password: {'*' * len(creds['password']) if creds['password'] else '(empty)'}")
    print(f"   Database: {creds['dbname']}")
    confirm = input(f"{Fore.YELLOW}✅  Is this correct? (y/n): {Style.RESET_ALL}").strip().lower()
    if confirm in ('y', 'yes'):
        return creds
    else:
        print(f"{Fore.RED}❌  Configuration cancelled. Re-run to enter again.")
        return None


def generate_real_config_php(folder, db_creds, db_vars):
    config_path = os.path.join(folder, 'config.php')
    var_to_const = {}
    for var_name in db_vars:
        const_name = var_name.upper()
        if not const_name.startswith('DB_'):
            const_name = 'DB_' + const_name
        var_to_const[var_name] = const_name

    host_var = user_var = pass_var = db_var = None
    for var in db_vars:
        lower = var.lower()
        if 'host' in lower:
            host_var = var
        elif 'user' in lower or 'username' in lower:
            user_var = var
        elif 'pass' in lower or 'password' in lower:
            pass_var = var
        elif 'name' in lower or 'dbname' in lower or 'database' in lower:
            db_var = var

    content = "<?php\n"
    content += "// Database Configuration - REAL CONNECTION\n"
    content += "// Generated by Web Downloader\n\n"
    if host_var:
        const_name = var_to_const.get(host_var, 'DB_HOST')
        content += f"define('{const_name}', '{db_creds['host']}');\n"
    else:
        content += f"define('DB_HOST', '{db_creds['host']}');\n"
    if user_var:
        const_name = var_to_const.get(user_var, 'DB_USER')
        content += f"define('{const_name}', '{db_creds['user']}');\n"
    else:
        content += f"define('DB_USER', '{db_creds['user']}');\n"
    if pass_var:
        const_name = var_to_const.get(pass_var, 'DB_PASS')
        content += f"define('{const_name}', '{db_creds['password']}');\n"
    else:
        content += f"define('DB_PASS', '{db_creds['password']}');\n"
    if db_var:
        const_name = var_to_const.get(db_var, 'DB_NAME')
        content += f"define('{const_name}', '{db_creds['dbname']}');\n"
    else:
        content += f"define('DB_NAME', '{db_creds['dbname']}');\n"
    content += "\n$conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);\n"
    content += "if ($conn->connect_error) {\n"
    content += "    die('Connection failed: ' . $conn->connect_error);\n"
    content += "}\n"
    content += "?>\n"
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"{Fore.GREEN}✅  Generated config.php with REAL credentials.")
    htaccess_path = os.path.join(folder, '.htaccess')
    htaccess_content = "<Files config.php>\n    Order Allow,Deny\n    Deny from all\n</Files>\n"
    with open(htaccess_path, 'w') as f:
        f.write(htaccess_content)
    print(f"{Fore.GREEN}✅  Created .htaccess to protect config.php")
    return True


def process_php_files(folder, db_vars):
    if not db_vars:
        return
    var_to_const = {}
    for var_name in db_vars:
        const_name = var_name.upper()
        if not const_name.startswith('DB_'):
            const_name = 'DB_' + const_name
        var_to_const[var_name] = const_name
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.php') and file != 'config.php':
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if 'config.php' not in content:
                        if content.startswith('<?php'):
                            content = content.replace('<?php', "<?php\nrequire_once 'config.php';\n", 1)
                        else:
                            content = "<?php\nrequire_once 'config.php';\n" + content
                    for var_name, const_name in var_to_const.items():
                        content = re.sub(r'\$' + re.escape(var_name) + r'\b', const_name, content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    print(f"{Fore.RED}✖  Error processing {file}: {e}")


def setup_realtime_database(folder):
    print(f"{Fore.YELLOW}🔗  SETTING UP REAL DATABASE CONNECTION")
    print(f"{Fore.CYAN}ℹ️  This will allow the downloaded website to connect to a REAL database.")
    print(f"{Fore.CYAN}ℹ️  You need to have a database server running (local or remote).")
    print("")

    db_vars = {}
    print(f"{Fore.CYAN}🔍  Scanning PHP files for database variables...")
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.php') and file != 'config.php':
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    vars_found = extract_db_variables(content)
                    if vars_found:
                        db_vars.update(vars_found)
                except Exception as e:
                    print(f"{Fore.RED}✖  Error reading {file}: {e}")

    if not db_vars:
        print(f"{Fore.YELLOW}⚠️  No database variables detected in PHP files.")
        print(f"{Fore.CYAN}💡  You can still create a config.php file manually.")
        print(f"{Fore.CYAN}💡  But the PHP code may not use it correctly.")
        if not ask_user_yes_no(f"{Fore.YELLOW}❓  Continue anyway? (y/n): "):
            return False
        db_vars = {'db_host': 'localhost', 'db_user': 'root', 'db_password': '', 'db_name': 'database'}

    creds = get_db_credentials_from_user()
    if not creds:
        return False

    generate_real_config_php(folder, creds, db_vars)
    process_php_files(folder, db_vars)

    print(f"{Fore.CYAN}\n📘  HOW TO RUN THE WEBSITE WITH DATABASE:")
    print(f"{Fore.YELLOW}1.  Copy the folder to your web server directory:")
    print(f"    - XAMPP: htdocs/{os.path.basename(folder)}")
    print(f"    - WAMP: www/{os.path.basename(folder)}")
    print(f"    - Linux: /var/www/html/{os.path.basename(folder)}")
    print(f"{Fore.YELLOW}2.  Start MySQL/MariaDB server")
    print(f"{Fore.YELLOW}3.  Create the database '{creds['dbname']}' (if it doesn't exist)")
    print(f"{Fore.YELLOW}4.  Import any SQL dump files if you have them")
    print(f"{Fore.YELLOW}5.  Open browser and go to:")
    print(f"    http://localhost/{os.path.basename(folder)}/index.html")
    print(f"{Fore.CYAN}📌  The config.php file contains your real credentials.")
    print(f"{Fore.CYAN}📌  It is protected by .htaccess (deny from all).")
    print(f"{Fore.CYAN}📌  Make sure to keep it secure!")
    return True


# ============================================================
# Selenium Rendering
# ============================================================

def render_page_with_selenium(url):
    if not SELENIUM_AVAILABLE:
        print(f"{Fore.RED}❌  Selenium not available.")
        return None
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        driver.quit()
        return html
    except Exception as e:
        print(f"{Fore.RED}❌  Selenium error: {e}")
        return None


# ============================================================
# Single File HTML (Base64 Embed)
# ============================================================

def embed_resources_as_base64(html_content, folder):
    soup = BeautifulSoup(html_content, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not src.startswith('data:'):
            local_path = os.path.join(folder, 'images', os.path.basename(src))
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'rb') as f:
                        data = base64.b64encode(f.read()).decode('utf-8')
                    mime = mimetypes.guess_type(local_path)[0] or 'image/png'
                    img['src'] = f'data:{mime};base64,{data}'
                except Exception as e:
                    print(f"{Fore.RED}⚠️  Failed to embed {src}: {e}")
    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href')
        if href and not href.startswith('data:'):
            local_path = os.path.join(folder, os.path.basename(href))
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        css = f.read()
                    style_tag = soup.new_tag('style')
                    style_tag.string = css
                    link.replace_with(style_tag)
                except Exception as e:
                    print(f"{Fore.RED}⚠️  Failed to embed CSS {href}: {e}")
    return str(soup)


# ============================================================
# Filters, Cleanup, Sitemap, Error Report
# ============================================================

def should_download_url(url):
    include = settings.get('include_patterns', [])
    exclude = settings.get('exclude_patterns', [])
    if exclude:
        for pattern in exclude:
            if re.search(pattern, url):
                return False
    if include:
        for pattern in include:
            if re.search(pattern, url):
                return True
        return False
    return True


def cleanup_empty_dirs(folder):
    if not settings.get('cleanup', True):
        return
    try:
        for root, dirs, files in os.walk(folder, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        print(f"{Fore.CYAN}🧹  Removed empty dir: {dir_path}")
                except OSError:
                    pass
    except Exception as e:
        print(f"{Fore.RED}⚠️  Cleanup error: {e}")


def generate_sitemap(folder):
    sitemap_path = os.path.join(folder, 'sitemap.json')
    try:
        with open(sitemap_path, 'w') as f:
            json.dump(download_state['sitemap'], f, indent=2)
        txt_path = os.path.join(folder, 'sitemap.txt')
        with open(txt_path, 'w') as f:
            for url in download_state['sitemap']:
                f.write(url + '\n')
        print(f"{Fore.GREEN}✅  Sitemap saved")
    except Exception as e:
        print(f"{Fore.RED}⚠️  Failed to save sitemap: {e}")


def generate_error_report(folder, failed_downloads):
    report_path = os.path.join(folder, 'error_report.txt')
    try:
        with open(report_path, 'w') as f:
            f.write("=== Web Downloader Error Report ===\n")
            f.write(f"Generated: {time.ctime()}\n")
            f.write(f"Total failed downloads: {len(failed_downloads)}\n\n")
            for url in failed_downloads:
                f.write(f"  {url}\n")
        print(f"{Fore.YELLOW}📄  Error report saved: {report_path}")
    except Exception as e:
        print(f"{Fore.RED}⚠️  Failed to save error report: {e}")


def ask_user_yes_no(prompt):
    if settings.get('batch_mode', False) and settings.get('auto_yes', False):
        print(f"{Fore.CYAN}⏩  Auto-answer YES: {prompt}")
        return True
    while True:
        answer = input(prompt).strip().lower()
        if not answer:
            print(f"{Fore.RED}⚠️  Input cannot be empty.")
            continue
        if answer in ('y', 'yes'):
            return True
        elif answer in ('n', 'no'):
            return False
        else:
            print(f"{Fore.RED}⚠️  Enter y or n.")


# ============================================================
# Main Download Function (Ultimate)
# ============================================================

def download_site(url, folder=None, visited_urls=None, depth=0, parent_folder=None, session=None):
    if visited_urls is None:
        visited_urls = set()
    if session is None:
        session = get_session()

    if not url.startswith(('http://', 'https://', 'ftp://')):
        url = 'http://' + url

    max_depth = settings.get('max_depth', 3)
    if depth > max_depth:
        print(f"{Fore.YELLOW}⏭️  Max depth reached: {url}")
        return folder

    if url in visited_urls:
        print(f"{Fore.YELLOW}⏩  Already visited: {url}")
        return folder
    visited_urls.add(url)
    download_state['visited_urls'].add(url)
    download_state['sitemap'].append(url)

    print(f"{Fore.BLUE}🌐  [{depth}] Processing: {url}")

    if folder is None:
        folder = create_folder_from_url(url)
    else:
        if parent_folder:
            sub_folder = create_folder_from_url(url)
            folder = os.path.join(parent_folder, sub_folder)
            os.makedirs(folder, exist_ok=True)
        else:
            folder = create_folder_from_url(url)

    load_download_state(folder)

    html_content = None
    if url.startswith('ftp://'):
        html_path = os.path.join(folder, 'index.html')
        success, content = download_ftp(url, html_path)
        if success:
            print(f"{Fore.GREEN}✅  FTP download successful")
            return folder
    else:
        try:
            if settings.get('use_selenium', False):
                html_content = render_page_with_selenium(url)
                if html_content is None:
                    response = session.get(url, timeout=settings.get('timeout', 15))
                    response.raise_for_status()
                    html_content = response.text
            else:
                response = session.get(url, timeout=settings.get('timeout', 15))
                response.raise_for_status()
                html_content = response.text
            base_url = response.url if 'response' in locals() else url
            html_path = os.path.join(folder, 'index.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"{Fore.GREEN}✅  HTML downloaded: index.html")
        except Exception as e:
            print(f"{Fore.RED}❌  Error downloading HTML: {e}")
            return folder

    if settings.get('save_single_file', False):
        html_content = embed_resources_as_base64(html_content, folder)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"{Fore.MAGENTA}🔄  HTML converted to single-file")
        return folder

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract resources
    inline_css = [style.string.strip() for style in soup.find_all('style') if style.string]
    inline_js = [script.string.strip() for script in soup.find_all('script', src=False) if script.string]
    print(f"{Fore.CYAN}ℹ️  Found {len(inline_css)} inline CSS, {len(inline_js)} inline JS")

    inline_css_files = []
    inline_js_files = []
    for i, content in enumerate(inline_css):
        filename = f"inline_style_{i+1}.css"
        path = os.path.join(folder, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        inline_css_files.append(filename)
    for i, content in enumerate(inline_js):
        filename = f"inline_script_{i+1}.js"
        path = os.path.join(folder, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        inline_js_files.append(filename)

    css_urls = extract_external_resources(soup, base_url, 'css')
    js_urls = extract_external_resources(soup, base_url, 'js')
    image_urls = extract_images_from_html(soup, base_url)
    font_urls = extract_fonts(soup, base_url) if settings.get('download_fonts', True) else set()
    media_urls = extract_media(soup, base_url) if settings.get('download_media', True) else set()
    data_urls = extract_data_files(soup, base_url) if settings.get('download_data', True) else set()

    all_urls = css_urls + js_urls + list(image_urls) + list(font_urls) + list(media_urls) + list(data_urls)
    filtered_urls = [u for u in all_urls if should_download_url(u)]

    resource_map = {'css': [], 'js': []}
    image_map = {}
    php_map = {}
    failed_downloads = []

    # Download images
    print(f"{Fore.YELLOW}🖼️  Downloading images...")
    if image_urls:
        download_resources_parallel(
            list(image_urls), base_url, folder, 'image',
            lambda url, base, fld, **kw: download_image(url, base, fld, image_map)
        )

    # Download CSS
    print(f"{Fore.YELLOW}🎨  Downloading CSS...")
    for css_url in css_urls:
        if not should_download_url(css_url):
            continue
        filename = os.path.basename(urlparse(css_url).path) or f"style_{len(resource_map['css'])+1}.css"
        save_path = os.path.join(folder, filename)
        success, content = download_file(css_url, save_path, session=session)
        if success and content:
            visited = set()
            content = process_css_imports(content, css_url, base_url, folder, visited, image_map)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            resource_map['css'].append((css_url, filename))
            print(f"{Fore.GREEN}   ✔  CSS: {filename}")
        else:
            if inline_css_files:
                fallback_file = inline_css_files.pop(0)
                fallback_path = os.path.join(folder, fallback_file)
                if os.path.exists(fallback_path):
                    shutil.copy(fallback_path, save_path)
                    resource_map['css'].append((css_url, filename))
                    print(f"{Fore.YELLOW}   ⚠️  Used inline fallback: {filename}")
            else:
                failed_downloads.append(css_url)
                print(f"{Fore.RED}   ✖  Failed: {filename}")

    # Download JS
    print(f"{Fore.YELLOW}⚡  Downloading JS...")
    for js_url in js_urls:
        if not should_download_url(js_url):
            continue
        filename = os.path.basename(urlparse(js_url).path) or f"script_{len(resource_map['js'])+1}.js"
        save_path = os.path.join(folder, filename)
        success, content = download_file(js_url, save_path, session=session)
        if success and content:
            visited = set()
            content = process_js_imports(content, js_url, base_url, folder, visited)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            resource_map['js'].append((js_url, filename))
            print(f"{Fore.GREEN}   ✔  JS: {filename}")
        else:
            if inline_js_files:
                fallback_file = inline_js_files.pop(0)
                fallback_path = os.path.join(folder, fallback_file)
                if os.path.exists(fallback_path):
                    shutil.copy(fallback_path, save_path)
                    resource_map['js'].append((js_url, filename))
                    print(f"{Fore.YELLOW}   ⚠️  Used inline fallback: {filename}")
            else:
                failed_downloads.append(js_url)
                print(f"{Fore.RED}   ✖  Failed: {filename}")

    # Download fonts, media, data
    for resource_type, urls in [
        ('fonts', font_urls),
        ('media', media_urls),
        ('data', data_urls),
    ]:
        if urls:
            print(f"{Fore.YELLOW}📦  Downloading {resource_type}...")
            for url in urls:
                if not should_download_url(url):
                    continue
                filename = os.path.basename(urlparse(url).path) or f"{resource_type}_{len(download_state['completed_files'])+1}.bin"
                save_path = os.path.join(folder, filename)
                success, _ = download_file(url, save_path, session=session)
                if success:
                    print(f"{Fore.GREEN}   ✔  {resource_type}: {filename}")
                else:
                    failed_downloads.append(url)
                    print(f"{Fore.RED}   ✖  Failed: {filename}")

    # PHP files
    print(f"{Fore.YELLOW}🐘  Extracting PHP files...")
    php_urls = extract_php_files(soup, base_url)
    if php_urls:
        for php_url in php_urls:
            if not should_download_url(php_url):
                continue
            filename = os.path.basename(urlparse(php_url).path) or f"script_{len(php_map)+1}.php"
            save_path = os.path.join(folder, filename)
            success, content = download_file(php_url, save_path, session=session)
            if success:
                php_map[php_url] = filename
                print(f"{Fore.GREEN}   ✔  PHP: {filename}")
            else:
                failed_downloads.append(php_url)
                print(f"{Fore.RED}   ✖  Failed: {filename}")

    # Update HTML
    try:
        updated_html = update_html_references(html_content, resource_map, image_map, php_map, base_url)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        print(f"{Fore.MAGENTA}🔄  HTML updated with local references")
    except Exception as e:
        print(f"{Fore.RED}💥  Error updating HTML: {e}")

    # Database setup - REAL CONNECTION
    print(f"{Fore.YELLOW}🐘  Database setup for real connection...")
    config_path = os.path.join(folder, 'config.php')
    has_config = os.path.exists(config_path)
    has_real_config = False
    if has_config:
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if '// Replace with actual value' not in content:
                has_real_config = True
        except:
            pass

    if has_real_config:
        print(f"{Fore.GREEN}✅  config.php already has real credentials. Skipping setup.")
    else:
        if ask_user_yes_no(f"{Fore.YELLOW}❓  Do you want to set up REAL database connection? (y/n): "):
            setup_realtime_database(folder)
        else:
            print(f"{Fore.CYAN}⏭️  Skipping database setup.")

    # External links
    if depth < max_depth:
        external_links = extract_external_links(soup, base_url)
        if external_links:
            print(f"{Fore.CYAN}🔗  Found {len(external_links)} external links")
            for ext_url in external_links:
                if ext_url in visited_urls:
                    continue
                if not should_download_url(ext_url):
                    continue
                if settings.get('batch_mode', False) and settings.get('auto_yes', False):
                    download_site(ext_url, folder=None, visited_urls=visited_urls, depth=depth+1, parent_folder=folder, session=session)
                else:
                    parsed = urlparse(ext_url)
                    domain = parsed.netloc
                    if ask_user_yes_no(f"{Fore.YELLOW}❓  Download '{domain}'? (y/n): "):
                        download_site(ext_url, folder=None, visited_urls=visited_urls, depth=depth+1, parent_folder=folder, session=session)
                    else:
                        print(f"{Fore.CYAN}⏭️  Skipping {domain}")

    # Finalize
    save_download_state(folder)
    if settings.get('generate_sitemap', True):
        generate_sitemap(folder)
    if failed_downloads:
        generate_error_report(folder, failed_downloads)
    cleanup_empty_dirs(folder)

    return folder


# ============================================================
# Main Entry Point
# ============================================================

def main():
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}🌐  ULTIMATE WEB DOWNLOADER v3.0")
    print(f"{Fore.CYAN}👤  Author: github.com/Mikaeil297")
    print(f"{Fore.CYAN}📦  15 Advanced Features + REAL Database Support")
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}1.  Fonts & Media    2. Multithreading    3. Resume")
    print(f"{Fore.CYAN}4.  Authentication    5. Proxy/User-Agent  6. Filters")
    print(f"{Fore.CYAN}7.  Single-File HTML  8. Max Depth        9. Sitemap")
    print(f"{Fore.CYAN}10. JS Rendering     11. Error Report    12. Batch Mode")
    print(f"{Fore.CYAN}13. Config File      14. Auto-Cleanup    15. FTP Support")
    print(f"{Fore.CYAN}16. REAL Database Connection (NEW!)")
    print(f"{Fore.CYAN}{'='*70}")

    if os.path.exists('settings.json'):
        print(f"{Fore.GREEN}✅  Loaded settings from settings.json")

    url = input(f"{Fore.GREEN}📎  Enter URL: {Style.RESET_ALL}").strip()
    if not url:
        print(f"{Fore.RED}❌  URL cannot be empty.")
        return
    if not url.startswith(('http://', 'https://', 'ftp://')):
        url = 'http://' + url

    print(f"{Fore.CYAN}ℹ️  Settings:")
    print(f"   Max workers: {settings.get('max_workers')}")
    print(f"   Max depth: {settings.get('max_depth')}")
    print(f"   Batch mode: {settings.get('batch_mode')}")
    print(f"   Auto yes: {settings.get('auto_yes')}")
    print(f"   Single-file: {settings.get('save_single_file')}")
    print(f"   Use Selenium: {settings.get('use_selenium') and SELENIUM_AVAILABLE}")

    visited = set()
    try:
        download_site(url, visited_urls=visited, session=get_session())
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}\n⏹️  Interrupted by user.")
    except Exception as e:
        print(f"{Fore.RED}💥  Unexpected error: {e}")
        import traceback
        traceback.print_exc()

    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.GREEN}✅  All operations completed!")
    print(f"{Fore.CYAN}📄  Check error_report.txt if something failed")
    print(f"{Fore.CYAN}📊  Sitemap generated in sitemap.json/txt")
    print(f"{Fore.CYAN}👤  Coded by github.com/Mikaeil297")
    print(f"{Fore.CYAN}{'='*70}")


if __name__ == "__main__":
    main()