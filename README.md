# WebFullGrab

**A complete webpage downloader with recursive CSS `@import` and JavaScript ES module support, plus smart inline fallback.**

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Author](https://img.shields.io/badge/Author-Mikaeil297-red)](https://github.com/mikaeil297)
[![GitHub stars](https://img.shields.io/github/stars/mikaeil297/WebFullGrab?style=social)](https://github.com/mikaeil297/WebFullGrab/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/mikaeil297/WebFullGrab?style=social)](https://github.com/mikaeil297/WebFullGrab/network/members)
[![GitHub issues](https://img.shields.io/github/issues/mikaeil297/WebFullGrab)](https://github.com/mikaeil297/WebFullGrab/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/mikaeil297/WebFullGrab)](https://github.com/mikaeil297/WebFullGrab/pulls)
[![Last Commit](https://img.shields.io/github/last-commit/mikaeil297/WebFullGrab)](https://github.com/mikaeil297/WebFullGrab/commits/main)

---

## 🚀 Features

- ✅ Downloads **HTML** and saves as `index.html`
- ✅ Extracts all **external CSS** and **JavaScript** files
- ✅ Recursively follows **`@import`** rules inside CSS files
- ✅ Recursively follows **ES module imports** (`import ... from '...'` and `import('...')`)
- ✅ **Smart fallback** to inline `<style>` / `<script>` if external file fails
- ✅ Automatically updates HTML references to point to **local files** (relative paths)
- ✅ Fully colored terminal output using `colorama`
- ✅ Clean, well-commented Python code

---

## 📸 Screenshot (Example Output)

```

🌐  WebFullGrab - Web Page Downloader & Resource Extractor
👤  Author: github.com/Mikaeil297
============================================================
📎  Enter the URL: https://example.com
🔍  Processing: https://example.com
📁  Created folder: example
✅  HTML downloaded: index.html
ℹ️  Found 2 inline CSS and 1 inline JS blocks.
🎨  Found 3 external CSS file(s). Downloading...
✔  Downloaded: style.css
✔  Downloaded: theme.css
✔  Downloaded: fonts.css
⚡  Found 2 external JS file(s). Downloading...
✔  Downloaded: main.js
✔  Downloaded: vendor.js
🔄  HTML updated with local file references.
============================================================
✅  Done! All files saved in: example/
📄 index.html  (updated)
🎨 style.css
🎨 theme.css
🎨 fonts.css
⚡ main.js
⚡ vendor.js
============================================================
👤  Coded by github.com/Mikaeil297

```

---

## 📦 How to Get the Code

### Option 1: Clone with Git
```bash
git clone https://github.com/mikaeil297/WebFullGrab.git
cd WebFullGrab
```

Option 2: Download ZIP

Go to https://github.com/mikaeil297/WebFullGrab and click the green "Code" button → "Download ZIP". Then extract the folder.

---

🔧 Installation (Dependencies)

This project requires Python 3.7 or higher.
Install the required libraries using pip:

```bash
pip install requests beautifulsoup4 colorama
```

📚 Libraries Used:

Library Purpose
requests Sending HTTP requests to download HTML, CSS, and JS files
beautifulsoup4 Parsing HTML to extract tags, attributes, and inline content
colorama Displaying colored and styled output in the terminal

---

🖥️ Usage

Run the script and enter the target URL when prompted:

```bash
python webfullgrab.py
```

Note: The main script file is webfullgrab.py. Make sure you are in the project directory.

---

📂 Output Structure

After execution, all files will be saved inside a folder named after the domain (e.g., example/).

```
example/
├── index.html          # Updated with local references
├── style.css           # Main stylesheet
├── theme.css           # Additional stylesheet
├── main.js             # Main JavaScript
├── import_1.css        # CSS file loaded via @import
├── import_2.js         # JS module loaded via import()
└── inline_style_1.css  # Inline CSS saved as fallback (if used)
```

---

🧠 How It Works

1. Download HTML from the provided URL.
2. Parse the HTML to locate:
   · <link rel="stylesheet"> → external CSS
   · <script src="..."> → external JS
   · Inline <style> and <script> (without src) → stored as fallback candidates.
3. For each external file:
   · Try to download it.
   · If successful, recursively scan its content for @import (CSS) or import (JS) and download those dependencies as well.
   · If the download fails, replace it with the first available inline block (fallback mechanism).
4. Update the original HTML to replace all remote URLs with local filenames.
5. Save every file inside the dedicated folder.

---

🛠️ Dependencies (Detailed)

Library Version Installation Command
Python 3.7+ python.org
requests latest pip install requests
beautifulsoup4 latest pip install beautifulsoup4
colorama latest pip install colorama

---

🏷️ Topics / Keywords

· web-scraping
· html-downloader
· css-extractor
· javascript-downloader
· import-resolver
· static-site-generator
· python-tool
· web-archiver

💡 Tip: Add these topics to your repository on GitHub (under "Manage topics") for better discoverability.

---

🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to open a pull request or an issue.
For major changes, please open an issue first to discuss what you would like to change.

---

⭐ Support

If you find this project useful, please consider giving it a star ⭐ on GitHub – it helps others discover it and motivates me to keep improving it!

---

📄 License

This project is licensed under the MIT License – see the LICENSE file for details.

---

👤 Author

Mikaeil – github.com/mikaeil297- ✅ Automatically updates HTML references to point to **local files** (relative paths)
- ✅ Fully colored terminal output using `colorama`
- ✅ Clean, well-commented Python code

---

## 📸 Screenshot (Example Output)

```

🌐  WebFullGrab - Web Page Downloader & Resource Extractor
👤  Author: github.com/Mikaeil297
============================================================
📎  Enter the URL: https://example.com
🔍  Processing: https://example.com
📁  Created folder: example
✅  HTML downloaded: index.html
ℹ️  Found 2 inline CSS and 1 inline JS blocks.
🎨  Found 3 external CSS file(s). Downloading...
✔  Downloaded: style.css
✔  Downloaded: theme.css
✔  Downloaded: fonts.css
⚡  Found 2 external JS file(s). Downloading...
✔  Downloaded: main.js
✔  Downloaded: vendor.js
🔄  HTML updated with local file references.
============================================================
✅  Done! All files saved in: example/
📄 index.html  (updated)
🎨 style.css
🎨 theme.css
🎨 fonts.css
⚡ main.js
⚡ vendor.js
============================================================
👤  Coded by github.com/Mikaeil297

```

---

## 📦 Installation

```bash
git clone https://github.com/mikaeil297/WebFullGrab.git
cd WebFullGrab
pip install requests beautifulsoup4 colorama
```

---

🖥️ Usage

Run the script and enter the target URL when prompted:

```bash
python webfullgrab.py
```

---

📂 Output Structure

After execution, all files will be saved inside a folder named after the domain (e.g., example/).

```
example/
├── index.html          # Updated with local references
├── style.css           # Main stylesheet
├── theme.css           # Additional stylesheet
├── main.js             # Main JavaScript
├── import_1.css        # CSS file loaded via @import
├── import_2.js         # JS module loaded via import()
└── inline_style_1.css  # Inline CSS saved as fallback (if used)
```

---

🧠 How It Works

1. Download HTML from the provided URL.
2. Parse the HTML to locate:
   · <link rel="stylesheet"> → external CSS
   · <script src="..."> → external JS
   · Inline <style> and <script> (without src) → stored as fallback candidates.
3. For each external file:
   · Try to download it.
   · If successful, recursively scan its content for @import (CSS) or import (JS) and download those dependencies as well.
   · If the download fails, replace it with the first available inline block (fallback mechanism).
4. Update the original HTML to replace all remote URLs with local filenames.
5. Save every file inside the dedicated folder.

---

🛠️ Dependencies

· requests – for making HTTP requests
· beautifulsoup4 – for parsing HTML
· colorama – for colored terminal output

---

🏷️ Topics / Keywords

· web-scraping
· html-downloader
· css-extractor
· javascript-downloader
· import-resolver
· static-site-generator
· python-tool
· web-archiver

💡 Tip: Add these topics to your repository on GitHub (under "Manage topics") for better discoverability.

---

🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to open a pull request or an issue.
For major changes, please open an issue first to discuss what you would like to change.

---

⭐ Support

If you find this project useful, please consider giving it a star ⭐ on GitHub – it helps others discover it and motivates me to keep improving it!

---

📄 License

This project is licensed under the MIT License – see the LICENSE file for details.

---

👤 Author

Mikaeil – github.com/mikaeil297

---

Happy downloading! 🚀
