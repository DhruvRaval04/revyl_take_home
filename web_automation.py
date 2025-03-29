from playwright.sync_api import sync_playwright
from typing import List, Dict, Optional
import time
from bs4 import BeautifulSoup

class WebAutomation:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def navigate_to(self, url: str) -> None:
        """Navigate to the specified URL"""
        self.page.goto(url)
        # Wait for the page to load
        self.page.wait_for_load_state('networkidle')

    def analyze_html(self) -> str:
        """Get the HTML content of the current page"""
        return self.page.content()

    def analyze_html_detailed(self) -> Dict:
        """
        Perform detailed HTML analysis of the current page
        
        Returns:
            Dict containing various HTML analysis metrics
        """
        html_content = self.page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        analysis = {
            'title': soup.title.string if soup.title else None,
            'meta_tags': {
                'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else None,
                'keywords': soup.find('meta', {'name': 'keywords'})['content'] if soup.find('meta', {'name': 'keywords'}) else None,
                'viewport': soup.find('meta', {'name': 'viewport'})['content'] if soup.find('meta', {'name': 'viewport'}) else None,
            },
            'headings': {
                'h1': [h1.text.strip() for h1 in soup.find_all('h1')],
                'h2': [h2.text.strip() for h2 in soup.find_all('h2')],
                'h3': [h3.text.strip() for h3 in soup.find_all('h3')],
            },
            'links': [{'text': a.text.strip(), 'href': a.get('href')} for a in soup.find_all('a', href=True)],
            'images': [{'alt': img.get('alt', ''), 'src': img.get('src')} for img in soup.find_all('img')],
            'scripts': [script.get('src') for script in soup.find_all('script', src=True)],
            'stylesheets': [link.get('href') for link in soup.find_all('link', rel='stylesheet')],
            'forms': [{'action': form.get('action'), 'method': form.get('method')} for form in soup.find_all('form')],
            'total_elements': len(soup.find_all()),
            'main_content': soup.find('main').text.strip() if soup.find('main') else None,
        }
        return analysis

    def take_screenshot(self, path: str = "screenshot.png") -> None:
        """Take a screenshot of the current page"""
        self.page.screenshot(path=path)

    def get_clickable_elements(self) -> List[Dict[str, str]]:
        """Get all clickable elements on the page"""
        clickable_elements = self.page.evaluate("""() => {
            const elements = [];
            const selectors = ['button', 'a', '[role="button"]', '[onclick]'];
            
            selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(element => {
                    if (element.offsetParent !== null) {  // Check if element is visible
                        elements.push({
                            tag: element.tagName.toLowerCase(),
                            text: element.textContent.trim(),
                            id: element.id,
                            class: element.className,
                            selector: selector
                        });
                    }
                });
            });
            return elements;
        }""")
        return clickable_elements

    def click_element(self, selector: str, timeout: int = 5000) -> bool:
        """Click an element based on the provided selector"""
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                element.click()
                return True
            return False
        except Exception as e:
            print(f"Error clicking element: {e}")
            return False

    def reload_page(self) -> None:
        """Reload the current page"""
        self.page.reload()
        # Wait for the page to load after reload
        self.page.wait_for_load_state('networkidle')

    def scroll(self, direction: str = "down", amount: int = 500, smooth: bool = True) -> None:
        """
        Scroll the page in the specified direction
        
        Args:
            direction (str): "up" or "down"
            amount (int): Number of pixels to scroll
            smooth (bool): Whether to use smooth scrolling
        """
        scroll_amount = amount if direction == "down" else -amount
        self.page.evaluate(f"""(amount, smooth) => {{
            window.scrollBy({{
                top: amount,
                behavior: smooth ? 'smooth' : 'auto'
            }});
        }}""", scroll_amount, smooth)
        # Small delay to allow smooth scrolling to complete
        time.sleep(0.5)

    def scroll_to_element(self, selector: str, timeout: int = 5000) -> bool:
        """
        Scroll to a specific element on the page
        
        Args:
            selector (str): CSS selector of the element to scroll to
            timeout (int): Maximum time to wait for the element in milliseconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                element.scroll_into_view_if_needed()
                return True
            return False
        except Exception as e:
            print(f"Error scrolling to element: {e}")
            return False

    def close(self) -> None:
        """Close the browser and playwright"""
        self.context.close()
        self.browser.close()
        self.playwright.stop()

# Example usage
if __name__ == "__main__":
    # Create an instance of the automation system
    automation = WebAutomation()
    
    try:
        # Navigate to a website
        automation.navigate_to("https://skyvern.com")
        
        # Get detailed HTML analysis
        html_analysis = automation.analyze_html_detailed()
        print("\nDetailed HTML Analysis:")
        print(f"Title: {html_analysis['title']}")
        print("\nMeta Tags:")
        for key, value in html_analysis['meta_tags'].items():
            print(f"- {key}: {value}")
        
        print("\nHeadings:")
        for level, headings in html_analysis['headings'].items():
            print(f"- {level}: {headings}")
        
        print(f"\nTotal Elements: {html_analysis['total_elements']}")
        print(f"Number of Links: {len(html_analysis['links'])}")
        print(f"Number of Images: {len(html_analysis['images'])}")
        print(f"Number of Scripts: {len(html_analysis['scripts'])}")
        print(f"Number of Stylesheets: {len(html_analysis['stylesheets'])}")
        print(f"Number of Forms: {len(html_analysis['forms'])}")
        
        # Take a screenshot
        automation.take_screenshot("example_screenshot.png")
        
        # Get clickable elements
        clickable_elements = automation.get_clickable_elements()
        print("\nClickable Elements:")
        for element in clickable_elements:
            print(f"- {element['tag']}: {element['text']}")
        
        # Example of scrolling
        # automation.scroll(direction="down", amount=500, smooth=True)
        # time.sleep(1)  # Wait a bit
        # automation.scroll(direction="up", amount=300, smooth=True)
        
        # Example of scrolling to a specific element
        # automation.scroll_to_element("footer")
        
        # Example of clicking an element (uncomment and modify selector as needed)
        # automation.click_element("button.submit-button")
        
        # Reload the page
        automation.reload_page()
        
    finally:
        # Always close the browser
        automation.close() 