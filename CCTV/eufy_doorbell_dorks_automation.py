#!/usr/bin/env python3
"""
Eufy Doorbell Google Dorks Automation Script (updated for Python 3 / Linux)

Changes made:
- Fixed parsing logic and syntax errors.
- Improved Selenium ChromeDriver initialization using webdriver-manager (auto-download).
- Added graceful fallbacks and helpful error messages for missing dependencies.
- Added --no-selenium / --browser option to run without Selenium (opens queries in default browser).
- Improved signal handling and driver cleanup for Linux terminal usage.

Use only for authorized security testing and ethical hacking.

Requirements:
    pip install selenium beautifulsoup4 requests webdriver-manager

Run:
    python3 eufy_doorbell_dorks_automation.py [options]
"""

import os
import sys
import time
import json
import csv
import argparse
import webbrowser
import signal
from datetime import datetime
from urllib.parse import quote
from typing import List, Dict
from pathlib import Path

# Optional imports for Selenium; provide helpful error message if missing
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

# webdriver-manager is optional but makes Linux usage much smoother by auto-installing chromedriver
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except Exception:
    WEBDRIVER_MANAGER_AVAILABLE = False


class EufyDorkAutomation:
    """Automate Google searches for Eufy doorbell security research"""

    GOOGLE_SEARCH_URL = "https://www.google.com/search"

    def __init__(self, headless: bool = True, delay: float = 2.0, timeout: int = 10, use_selenium: bool = True):
        """
        Initialize the automation script

        Args:
            headless: Run browser in headless mode (default True for Linux terminal)
            delay: Delay between requests in seconds
            timeout: Webdriver timeout in seconds
            use_selenium: Whether to use Selenium (if False, opens queries in the default browser)
        """
        self.delay = delay
        self.timeout = timeout
        self.headless = headless
        self.use_selenium = use_selenium
        self.results: List[Dict] = []
        self.driver = None
        self._interrupted = False

        # Install a signal handler so Ctrl-C closes the driver cleanly
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        print("\n⚠️  Interrupt received, shutting down...")
        self._interrupted = True
        self.close_driver()
        sys.exit(1)

    def init_driver(self) -> webdriver.Chrome:
        """Initialize Chrome WebDriver (tries webdriver-manager first, then falls back to system chromedriver)"""
        if not SELENIUM_AVAILABLE:
            print("⚠️  Selenium is not installed. Install it with: pip install selenium")
            sys.exit(1)

        chrome_options = ChromeOptions()
        # Use the modern headless flag if available; fallback to legacy --headless
        if self.headless:
            try:
                chrome_options.add_argument("--headless=new")
            except Exception:
                chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
        )

        # Try to use webdriver-manager on Linux which avoids manual chromedriver handling
        try:
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Fall back to system chromedriver in PATH
                self.driver = webdriver.Chrome(options=chrome_options)

            self.driver.set_page_load_timeout(self.timeout)
            return self.driver

        except Exception as e:
            print(f"❌ Failed to initialize Chrome driver: {e}")
            if not WEBDRIVER_MANAGER_AVAILABLE:
                print("   Consider installing webdriver-manager to auto-install ChromeDriver:")
                print("     pip install webdriver-manager")
            print("   Make sure Google Chrome / Chromium and chromedriver are installed and chromedriver is in your PATH.")
            sys.exit(1)

    def close_driver(self):
        """Close the WebDriver"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception:
            pass

    def extract_dorks_from_file(self, filepath: str) -> Dict[str, List[str]]:
        """
        Extract Google dorks from the dorks file organized by category

        The expected format is simple:
        - Category headers start with '# ' (hash followed by space). Example: '# API Endpoints'
        - Comment lines starting with '#' (without space) are ignored
        - Empty lines are ignored
        - Other lines are treated as dork queries and grouped under the most recent category
        """
        dorks: Dict[str, List[str]] = {}
        current_category = "General"

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    # Category header line: '# Category Name'
                    if line.startswith("# "):
                        current_category = line[2:].strip()
                        if current_category not in dorks:
                            dorks[current_category] = []
                        continue
                    # Full-line comment (ignore)
                    if line.startswith("#"):
                        continue

                    # Regular dork/query line
                    if current_category not in dorks:
                        dorks[current_category] = []
                    dorks[current_category].append(line)

        except FileNotFoundError:
            print(f"❌ File not found: {filepath}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading dorks file: {e}")
            sys.exit(1)

        return dorks

    def search_query(self, query: str, open_browser: bool = False) -> Dict:
        """
        Execute a single Google search query
        """
        try:
            search_url = f"{self.GOOGLE_SEARCH_URL}?q={quote(query)}"

            if open_browser or not self.use_selenium:
                # Open in user's default browser (useful when running without Selenium)
                print(f"🌐 Opening in browser: {query}")
                webbrowser.open(search_url)
            else:
                if not self.driver:
                    self.init_driver()
                print(f"🔍 Searching: {query}")
                self.driver.get(search_url)
                # simple wait - Selenium waits for page load, but allow small delay for dynamic content
                time.sleep(min(self.delay, 5.0))

            result = {
                "query": query,
                "url": search_url,
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
            }
            return result

        except Exception as e:
            print(f"❌ Error searching '{query}': {e}")
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
            }

    def run_automated_search(self, dorks_file: str, category: str = None, limit: int = None, open_browser: bool = False) -> List[Dict]:
        """
        Run automated searches for all or selected dorks
        """
        dorks = self.extract_dorks_from_file(dorks_file)

        # Filter by category if specified
        if category:
            if category not in dorks:
                print(f"❌ Category '{category}' not found. Available: {list(dorks.keys())}")
                return []
            dorks = {category: dorks[category]}

        # Initialize driver only if using Selenium
        if self.use_selenium and not open_browser:
            self.init_driver()

        total_queries = sum(len(queries) for queries in dorks.values())
        if limit:
            total_queries = min(total_queries, limit)

        print("\n📊 Starting automated Google dork searches")
        print(f"   Categories: {len(dorks)}")
        print(f"   Total queries to execute: {total_queries}\n")

        executed = 0

        try:
            for cat_name, queries in dorks.items():
                if self._interrupted:
                    break
                print(f"\n📁 Category: {cat_name} ({len(queries)} queries)")
                print("-" * 60)

                for i, query in enumerate(queries, 1):
                    if self._interrupted:
                        break
                    if limit and executed >= limit:
                        break

                    result = self.search_query(query, open_browser=open_browser or (not self.use_selenium))
                    self.results.append(result)
                    executed += 1

                    print(f"   [{executed}/{total_queries}] ✅ {result.get('status', 'unknown')}")

                    # Delay between queries to be polite
                    if i < len(queries) and not (open_browser or not self.use_selenium):
                        time.sleep(self.delay)

        except KeyboardInterrupt:
            print("\n⚠️  Search interrupted by user")

        finally:
            if self.driver:
                self.close_driver()

        print(f"\n✅ Completed {executed} searches")
        return self.results

    def save_results(self, output_file: str, format: str = "json"):
        """
        Save search results to file
        """
        if not self.results:
            print("⚠️  No results to save")
            return

        try:
            if format.lower() == "json":
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)

            elif format.lower() == "csv":
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    # Ensure all result dicts have the same keys
                    fieldnames = set()
                    for r in self.results:
                        fieldnames.update(r.keys())
                    fieldnames = list(fieldnames)
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.results)

            print(f"💾 Results saved to: {output_file}")

        except Exception as e:
            print(f"❌ Error saving results: {e}")

    def generate_report(self, output_file: str):
        """Generate a detailed search report"""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("EUFY DOORBELL GOOGLE DORKS - SEARCH REPORT\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Searches: {len(self.results)}\n")
                f.write(f"Successful: {sum(1 for r in self.results if r.get('status') == 'completed')}\n")
                f.write(f"Failed: {sum(1 for r in self.results if r.get('status') == 'failed')}\n\n")

                f.write("-" * 70 + "\n")
                f.write("SEARCH DETAILS\n")
                f.write("-" * 70 + "\n\n")

                for i, result in enumerate(self.results, 1):
                    f.write(f"[{i}] Query: {result.get('query', 'N/A')}\n")
                    f.write(f"    Status: {result.get('status', 'unknown')}\n")
                    f.write(f"    URL: {result.get('url', 'N/A')}\n")
                    if result.get('error'):
                        f.write(f"    Error: {result.get('error')}\n")
                    f.write(f"    Timestamp: {result.get('timestamp', 'N/A')}\n\n")

            print(f"📄 Report saved to: {output_file}")

        except Exception as e:
            print(f"❌ Error generating report: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Automate Eufy doorbell Google dorks security research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all searches
  python3 eufy_doorbell_dorks_automation.py

  # Run specific category
  python3 eufy_doorbell_dorks_automation.py --category "API Endpoints & Backend"

  # Open in browser instead of automated Selenium
  python3 eufy_doorbell_dorks_automation.py --browser --no-selenium

  # Limit to 10 queries
  python3 eufy_doorbell_dorks_automation.py --limit 10

  # Save results as CSV
  python3 eufy_doorbell_dorks_automation.py --output results.csv --format csv
        """,
    )

    parser.add_argument(
        "dorks_file",
        nargs="?",
        default="eufy-doorbell-dorks.txt",
        help="Path to dorks file (default: eufy-doorbell-dorks.txt)",
    )
    parser.add_argument("--category", help="Specific category to search")
    parser.add_argument("--limit", type=int, help="Maximum number of queries to execute")
    parser.add_argument(
        "--delay", type=float, default=2.0, help="Delay between requests in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Open results in browser (opens each query URL in default browser)",
    )
    parser.add_argument(
        "--no-selenium",
        action="store_true",
        help="Do not use Selenium even if installed; opens queries in the default browser",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: True when using Selenium)",
    )
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--report", help="Generate detailed report file")

    args = parser.parse_args()

    # Ensure Python 3
    if sys.version_info.major < 3:
        print("❌ Python 3 is required. Run with: python3 eufy_doorbell_dorks_automation.py")
        sys.exit(1)

    # Verify dorks file exists
    if not Path(args.dorks_file).exists():
        print(f"❌ Dorks file not found: {args.dorks_file}")
        sys.exit(1)

    use_selenium = (not args.no_selenium) and (not args.browser)

    # Initialize automation
    automation = EufyDorkAutomation(headless=(args.headless or True), delay=args.delay, use_selenium=use_selenium)

    # Run searches
    automation.run_automated_search(
        dorks_file=args.dorks_file,
        category=args.category,
        limit=args.limit,
        open_browser=(args.browser or args.no_selenium),
    )

    # Save results
    if args.output:
        automation.save_results(args.output, format=args.format)

    # Generate report
    if args.report:
        automation.generate_report(args.report)


if __name__ == "__main__":
    main()
