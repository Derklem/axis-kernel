import sys
from playwright.sync_api import sync_playwright

BROWSER_PROFILE = r"D:\Infinite\Infinity\Communication\BrowserProfile"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def get_metrics(url):
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE,
            headless=False,
            executable_path=CHROME_PATH
        )
        page = context.new_page()
        print(f"Navigating to {url}...")
        page.goto(url, timeout=60000)
        try:
            page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)
            article_text = page.locator('article[data-testid="tweet"]').first.inner_text()
            print(f"\n--- Data for {url} ---")
            print(article_text)
            print("------------------------\n")
        except Exception as e:
            print(f"Failed to extract metrics for {url}: {e}")
        finally:
            context.close()

if __name__ == "__main__":
    urls = [
        "https://x.com/DerekLamb29985/status/2075352705946755446",
        "https://x.com/DerekLamb29985/status/2075034406323179943"
    ]
    for u in urls:
        get_metrics(u)
