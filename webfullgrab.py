# Author: github.com/Mikaeil297
# Description: Full webpage downloader with inline fallback, @import and ES module support.

import os
import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

# Initialize colors for terminal
init(autoreset=True)


def create_folder_from_url(url):
    """Create a folder using the domain name."""
    parsed = urlparse(url)
    folder_name = parsed.netloc.replace("www.", "").split(".")[0]
    if not folder_name:
        folder_name = "downloaded_page"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def download_file(url, save_path):
    """Download a file from URL and save to save_path. Return (success, content)."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True, response.text if 'text' in response.headers.get('content-type', '') else None
    except Exception as e:
        print(f"{Fore.RED}⚠️  Failed to download {url}: {e}")
        return False, None


def get_absolute_url(base_url, link):
    """Convert relative link to absolute URL."""
    return urljoin(base_url, link)


def extract_inline_resources(soup, resource_type):
    """
    Extract inline CSS (<style>) or JS (<script> without src) content.
    Returns a list of strings (content).
    """
    contents = []
    if resource_type == 'css':
        for tag in soup.find_all('style'):
            if tag.string:
                contents.append(tag.string.strip())
    elif resource_type == 'js':
        for tag in soup.find_all('script', src=False):
            if tag.string:
                contents.append(tag.string.strip())
    return contents


def extract_external_resources(soup, base_url, resource_type):
    """Extract external CSS or JS URLs from HTML."""
    resources = []
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
    return resources


def process_css_imports(css_content, css_url, base_url, folder, downloaded_files, visited_imports):
    """
    Find all @import rules in CSS, download them recursively,
    and update the CSS content with local filenames.
    """
    import_pattern = r'@import\s+url\([\'"]?([^\'")]+)[\'"]?\)|@import\s+[\'"]([^\'"]+)[\'"]'
    imports = re.findall(import_pattern, css_content)
    # imports is a list of tuples (url_from_url, url_from_string)
    for url_tuple in imports:
        import_url = url_tuple[0] or url_tuple[1]
        if not import_url:
            continue
        absolute_url = get_absolute_url(base_url, import_url)
        if absolute_url in visited_imports:
            continue
        visited_imports.add(absolute_url)

        # Generate a filename for the imported file
        parsed = urlparse(absolute_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"import_{len(visited_imports)}.css"
        save_path = os.path.join(folder, filename)

        success, content = download_file(absolute_url, save_path)
        if success and content:
            # Recursively process imports in this imported file
            content = process_css_imports(content, absolute_url, base_url, folder, downloaded_files, visited_imports)
            # Update the imported file with modified content
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            # Update the original css_content: replace the import URL with local filename
            # We replace the whole import statement with the local filename
            # Using regex to replace the matched import
            # We need to replace the exact match in original content, but careful with quotes.
            # Simpler: replace the URL part with filename
            css_content = css_content.replace(import_url, filename)
        else:
            # If download failed, leave the import as is (or try to fallback?)
            # We'll keep the original URL
            pass

    return css_content


def process_js_imports(js_content, js_url, base_url, folder, downloaded_files, visited_imports):
    """
    Find ES module import statements (import ... from '...' or import('...'))
    and download them recursively, updating paths to local filenames.
    """
    # Pattern for static imports: import ... from '...' or import "..." 
    static_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
    # Pattern for dynamic import: import('...')
    dynamic_pattern = r'import\s*\([\'"]([^\'"]+)[\'"]\)'

    all_matches = re.findall(static_pattern, js_content)
    all_matches += re.findall(dynamic_pattern, js_content)

    for import_path in set(all_matches):
        if not import_path:
            continue
        absolute_url = get_absolute_url(base_url, import_path)
        if absolute_url in visited_imports:
            continue
        visited_imports.add(absolute_url)

        parsed = urlparse(absolute_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"import_{len(visited_imports)}.js"
        save_path = os.path.join(folder, filename)

        success, content = download_file(absolute_url, save_path)
        if success and content:
            # Recursively process imports inside this file
            content = process_js_imports(content, absolute_url, base_url, folder, downloaded_files, visited_imports)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            # Update the import path in the current js_content
            js_content = js_content.replace(import_path, filename)
        else:
            # If download fails, keep original path
            pass

    return js_content


def update_html_references(html_content, resource_map):
    """
    Update HTML to point to local files.
    resource_map: dict with keys 'css' and 'js', each a list of (original_url, local_filename)
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Update CSS links
    for tag in soup.find_all('link', rel='stylesheet'):
        href = tag.get('href')
        if href:
            # Find matching local filename by comparing absolute URL
            # We'll use a simple replacement: if href is in resource_map
            for orig_url, local_name in resource_map.get('css', []):
                if href == orig_url or href.endswith(orig_url):
                    tag['href'] = local_name
                    break

    # Update JS scripts
    for tag in soup.find_all('script', src=True):
        src = tag.get('src')
        if src:
            for orig_url, local_name in resource_map.get('js', []):
                if src == orig_url or src.endswith(orig_url):
                    tag['src'] = local_name
                    break

    return str(soup)


def main():
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}🌐  Web Page Downloader & Resource Extractor")
    print(f"{Fore.CYAN}👤  Author: github.com/Mikaeil297")
    print(f"{Fore.CYAN}{'='*60}")

    url = input(f"{Fore.GREEN}📎  Enter the URL: {Style.RESET_ALL}").strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    print(f"{Fore.BLUE}🔍  Processing: {url}")

    # Create folder
    folder = create_folder_from_url(url)
    print(f"{Fore.MAGENTA}📁  Created folder: {folder}")

    # Download HTML
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        html_content = response.text
        html_path = os.path.join(folder, 'index.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"{Fore.GREEN}✅  HTML downloaded: index.html")
    except Exception as e:
        print(f"{Fore.RED}❌  Error downloading HTML: {e}")
        return

    base_url = response.url
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract inline resources (for fallback)
    inline_css = extract_inline_resources(soup, 'css')
    inline_js = extract_inline_resources(soup, 'js')
    print(f"{Fore.CYAN}ℹ️  Found {len(inline_css)} inline CSS and {len(inline_js)} inline JS blocks.")

    # Save inline resources as separate files (for possible fallback)
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

    # Extract external resources
    css_urls = extract_external_resources(soup, base_url, 'css')
    js_urls = extract_external_resources(soup, base_url, 'js')

    resource_map = {'css': [], 'js': []}  # (original_url, local_filename)

    # Process CSS external files
    if css_urls:
        print(f"{Fore.YELLOW}🎨  Found {len(css_urls)} external CSS file(s). Downloading...")
        for idx, css_url in enumerate(css_urls):
            filename = os.path.basename(urlparse(css_url).path)
            if not filename:
                filename = f"style_{idx+1}.css"
            save_path = os.path.join(folder, filename)
            success, content = download_file(css_url, save_path)
            if success and content:
                # Process @imports recursively
                visited = set()
                content = process_css_imports(content, css_url, base_url, folder, resource_map, visited)
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                resource_map['css'].append((css_url, filename))
                print(f"{Fore.GREEN}   ✔  Downloaded: {filename}")
            else:
                # Fallback to inline CSS if available
                if inline_css_files:
                    fallback_file = inline_css_files.pop(0)  # use first available inline
                    # Copy inline content to the external filename
                    fallback_path = os.path.join(folder, fallback_file)
                    if os.path.exists(fallback_path):
                        import shutil
                        shutil.copy(fallback_path, save_path)
                        resource_map['css'].append((css_url, filename))
                        print(f"{Fore.YELLOW}   ⚠️  Used inline fallback for: {filename}")
                    else:
                        print(f"{Fore.RED}   ✖  Failed and no inline fallback for: {filename}")
                else:
                    print(f"{Fore.RED}   ✖  Failed to download and no inline fallback: {filename}")
    else:
        print(f"{Fore.CYAN}ℹ️  No external CSS found.")

    # Process JS external files
    if js_urls:
        print(f"{Fore.YELLOW}⚡  Found {len(js_urls)} external JS file(s). Downloading...")
        for idx, js_url in enumerate(js_urls):
            filename = os.path.basename(urlparse(js_url).path)
            if not filename:
                filename = f"script_{idx+1}.js"
            save_path = os.path.join(folder, filename)
            success, content = download_file(js_url, save_path)
            if success and content:
                # Process ES module imports recursively
                visited = set()
                content = process_js_imports(content, js_url, base_url, folder, resource_map, visited)
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                resource_map['js'].append((js_url, filename))
                print(f"{Fore.GREEN}   ✔  Downloaded: {filename}")
            else:
                # Fallback to inline JS if available
                if inline_js_files:
                    fallback_file = inline_js_files.pop(0)
                    fallback_path = os.path.join(folder, fallback_file)
                    if os.path.exists(fallback_path):
                        import shutil
                        shutil.copy(fallback_path, save_path)
                        resource_map['js'].append((js_url, filename))
                        print(f"{Fore.YELLOW}   ⚠️  Used inline fallback for: {filename}")
                    else:
                        print(f"{Fore.RED}   ✖  Failed and no inline fallback for: {filename}")
                else:
                    print(f"{Fore.RED}   ✖  Failed to download and no inline fallback: {filename}")
    else:
        print(f"{Fore.CYAN}ℹ️  No external JS found.")

    # Update HTML with local references
    updated_html = update_html_references(html_content, resource_map)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(updated_html)
    print(f"{Fore.MAGENTA}🔄  HTML updated with local file references.")

    # Final output
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}✅  Done! All files saved in: {folder}/")
    print(f"{Fore.YELLOW}   📄 index.html  (updated)")
    for _, fname in resource_map.get('css', []):
        print(f"   🎨 {fname}")
    for _, fname in resource_map.get('js', []):
        print(f"   ⚡ {fname}")
    # Also list any inline files that were not used as fallback (if any)
    if inline_css_files or inline_js_files:
        print(f"{Fore.CYAN}   📦 Additional inline files saved (not used as fallback):")
        for f in inline_css_files:
            print(f"      🎨 {f}")
        for f in inline_js_files:
            print(f"      ⚡ {f}")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}👤  Coded by github.com/Mikaeil297")


if __name__ == "__main__":
    main()
