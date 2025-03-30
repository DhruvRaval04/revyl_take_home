from playwright.async_api import async_playwright
from typing import List, Dict, Optional
import time
from bs4 import BeautifulSoup
import asyncio


class WebAutomation:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.loop = asyncio.get_event_loop()

    async def initialize(self):
        """Initialize the browser and context"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def navigate_to(self, url: str) -> None:
        """Navigate to the specified URL"""
        await self.page.goto(url)
        # Wait for the page to load
        await self.page.wait_for_load_state('networkidle')

    async def analyze_html(self) -> str:
        """Get the HTML content of the current page"""
        return await self.page.content()

    async def analyze_html_detailed(self) -> Dict:
        """
        Perform detailed HTML analysis of the current page
        
        Returns:
            Dict containing various HTML analysis metrics
        """
        html_content = await self.page.content()
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

    async def take_screenshot(self, path: str = "screenshot.png") -> None:
        """Take a screenshot of the current page"""
        await self.page.screenshot(path=path)

    async def get_clickable_elements(self) -> List[Dict[str, str]]:
        """Get all clickable elements on the page"""
        clickable_elements = await self.page.evaluate("""() => {
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

    async def click_element(self, selector: str, timeout: int = 5000) -> bool:
        """Click an element based on the provided selector"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                await element.click(force=True)
                return True
            return False
        except Exception as e:
            print(f"Error clicking element: {e}")
            return False

    async def click_all_book_demo_buttons(self):
        """Find and click all elements containing 'Book a Demo'."""
        try:
            elements = await self.page.query_selector_all("a:has-text('Book a demo')")
            
            for element in elements:
                try:
                    await element.click(force=True)
                    print("Clicked 'Book a demo' button.")
                    return True  # Exit after first successful click
                except Exception as click_error:
                    print(f"Error clicking element: {click_error}")
                    continue  # Try next element if this one fails

            return False  # Return False if no elements were clicked successfully
        except Exception as e:
            print(f"Error finding 'Book a demo' buttons: {e}")
            return False
    
    async def reload_page(self) -> None:
        """Reload the current page"""
        await self.page.reload()
        # Wait for the page to load after reload
        await self.page.wait_for_load_state('networkidle')

    async def accept_cookies(self):
        """Check if 'Accept Cookies' button exists and click it"""
        clickable_elements = await self.get_clickable_elements()
        
        for element in clickable_elements:
            if element["text"] == "Accept Cookies":
                return await self.click_element(f'#{element["id"]}' if element["id"] else element["selector"])
        
        print("Accept Cookies button not found.")
        return False


    async def scroll(self, direction: str = "down", amount: int = 500, smooth: bool = True) -> None:
        """
        Scroll the page in the specified direction
        
        Args:
            direction (str): "up" or "down"
            amount (int): Number of pixels to scroll
            smooth (bool): Whether to use smooth scrolling
        """
        scroll_amount = amount if direction == "down" else -amount
        await self.page.evaluate(f"""(amount, smooth) => {{
            window.scrollBy({{
                top: amount,
                behavior: smooth ? 'smooth' : 'auto'
            }});
        }}""", scroll_amount, smooth)
        # Small delay to allow smooth scrolling to complete
        await asyncio.sleep(0.5)

    async def scroll_to_element(self, selector: str, timeout: int = 5000) -> bool:
        """
        Scroll to a specific element on the page
        
        Args:
            selector (str): CSS selector of the element to scroll to
            timeout (int): Maximum time to wait for the element in milliseconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                await element.scroll_into_view_if_needed()
                return True
            return False
        except Exception as e:
            print(f"Error scrolling to element: {e}")
            return False

    async def fill_form_fields(self, fields: Dict[str, str], timeout: int = 5000) -> Dict[str, bool]:
        """
        Fill multiple form fields with their respective values
        
        Args:
            fields (Dict[str, str]): Dictionary of selectors and their values
            timeout (int): Maximum time to wait for each element in milliseconds
            
        Returns:
            Dict[str, bool]: Dictionary indicating success/failure for each field
        """
        results = {}
        for selector, value in fields.items():
            try:
                element = await self.page.wait_for_selector(selector, timeout=timeout)
                if element:
                    await element.fill(value)
                    results[selector] = True
                else:
                    results[selector] = False
            except Exception as e:
                print(f"Error filling field {selector}: {e}")
                results[selector] = False
        return results

    async def close(self) -> None:
        """Close the browser and playwright"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # Synchronous wrapper methods for compatibility with the agent workflow
    def sync_initialize(self) -> None:
        """Synchronous wrapper for initialize"""
        return self.loop.run_until_complete(self.initialize())

    def sync_navigate_to(self, url: str) -> None:
        """Synchronous wrapper for navigate_to"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.navigate_to(url))

    def sync_analyze_html_detailed(self) -> Dict:
        """Synchronous wrapper for analyze_html_detailed"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.analyze_html_detailed())

    def sync_get_clickable_elements(self) -> List[Dict[str, str]]:
        """Synchronous wrapper for get_clickable_elements"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.get_clickable_elements())

    def sync_click_element(self, selector: str) -> bool:
        """Synchronous wrapper for click_element"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.click_element(selector))
    
    def sync_click_all_book_demo_buttons(self):
        """Synchronous wrapper for click_all_book_demo_buttons"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.click_all_book_demo_buttons())

    def sync_fill_form_fields(self, fields: Dict[str, str]) -> Dict[str, bool]:
        """Synchronous wrapper for fill_form_fields"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.fill_form_fields(fields))

    def sync_take_screenshot(self, path: str = "screenshot.png") -> None:
        """Synchronous wrapper for take_screenshot"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.take_screenshot(path))
    
    def sync_accept_cookies(self):
        """Synchronous wrapper for accept_cookies"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.accept_cookies())

    def sync_reload_page(self) -> None:
        """Synchronous wrapper for reload_page"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.reload_page())

    def sync_close(self) -> None:
        """Synchronous wrapper for close"""
        if not self.page:
            return
        return self.loop.run_until_complete(self.close())

# Example usage
if __name__ == "__main__":
    # Create an instance of the automation system
    automation = WebAutomation()
    
    try:
        # Initialize the browser
        automation.sync_initialize()
        
        # Navigate to a website
        automation.sync_navigate_to("https://scale.com")
        automation.sync_accept_cookies()
        # Get detailed HTML analysis
        html_analysis = automation.sync_analyze_html_detailed()
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
        automation.sync_take_screenshot("example_screenshot.png")
        
        # Get clickable elements
        clickable_elements = automation.sync_get_clickable_elements()
        print(clickable_elements)
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
        automation.sync_reload_page()
        
    finally:
        # Always close the browser
        automation.sync_close() 