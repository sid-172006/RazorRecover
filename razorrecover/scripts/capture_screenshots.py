from playwright.sync_api import sync_playwright
import time

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1360, 'height': 850})
        
        print("Navigating to Simulator...")
        page.goto('http://localhost:3000/simulator')
        time.sleep(2)
        
        # Click Ambiguous Decline card
        page.locator('div:has-text("Ambiguous Decline (Gemini AI Fallback)")').last.click()
        time.sleep(1)
        
        # Click Simulate Customer Payment
        page.locator('button:has-text("Simulate Customer Payment")').click()
        print("Triggered simulation for Gemini Ambiguous decline...")
        time.sleep(7)
        
        page.screenshot(path='docs/screenshots/gemini_ai_recovery.png')
        print("Saved docs/screenshots/gemini_ai_recovery.png")
        
        browser.close()

if __name__ == '__main__':
    capture()
