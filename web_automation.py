from playwright.async_api import async_playwright
from typing import List, Dict, Optional
import time
from bs4 import BeautifulSoup
import asyncio
import logging
import traceback

class WebAutomation:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
         # Don't use get_event_loop() directly
        # Instead, create a new loop for each thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # self.loop = asyncio.get_event_loop()

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

    async def take_screenshot(self, path: str = "screenshot.png", timeout: int = 5000) -> None:
        """Take a screenshot of the current page"""
        await self.page.wait_for_load_state("load")
        await self.page.screenshot(path=path, timeout=timeout)

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
    
    async def click_and_switch_to_new_tab(self, selector: str, timeout: int = 5000) -> bool:
        """
        Click an element and switch to the new tab if one is opened.
        
        Args:
            selector (str): CSS selector of the element to click.
            timeout (int): Maximum time to wait for the element in milliseconds.
        
        Returns:
            bool: True if the click was successful, False otherwise.
        """
        try:
            # Record the current number of pages
            current_pages = len(self.context.pages)
            # Wait for the element and click it
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                await element.click(force=True)
                # Brief pause to allow the new tab to open
                await asyncio.sleep(1)
                # Check if a new page was opened
                if len(self.context.pages) > current_pages:
                    # Switch to the newest page (last in the list)
                    self.page = self.context.pages[-1]
                    # Wait for the new page to fully load
                    await self.page.wait_for_load_state('networkidle')
                return True
            return False
        except Exception as e:
            print(f"Error clicking element and switching to new tab: {e}")
            return False

    async def click_all_book_demo_buttons(self):
        """
        Find and click all 'Book a Demo' elements, switching to new tab if opened.
        """
        try:
            elements = await self.page.query_selector_all("a:has-text('Book a demo')")
            for element in elements:
                try:
                    current_pages = len(self.context.pages)
                    await element.click(force=True)
                    await asyncio.sleep(1)
                    if len(self.context.pages) > current_pages:
                        self.page = self.context.pages[-1]
                        await self.page.wait_for_load_state('networkidle')
                    print("Clicked 'Book a demo' button.")
                    return True
                except Exception as click_error:
                    print(f"Error clicking element: {click_error}")
                    continue
            return False
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
        
        # Pass parameters as a single object
        await self.page.evaluate("""
            ({amount, smooth}) => {
                window.scrollBy({
                    top: amount,
                    behavior: smooth ? 'smooth' : 'auto'
                });
            }
        """, {"amount": scroll_amount, "smooth": smooth})
        
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
    
    async def fill_form_fields(self, fields: Dict[str, str], timeout: int = 5000) -> Dict[str, bool]:
        """
        Fill form fields based on their labels
        
        Args:
            fields (Dict[str, str]): Dictionary of field labels and their values
            timeout (int): Maximum time to wait for elements in milliseconds
            
        Returns:
            Dict[str, bool]: Dictionary indicating success/failure for each field
        """
        results = {}
        for field_label, value in fields.items():
            try:
                # Clean up the field label - remove asterisks and trim
                clean_label = field_label.replace('*', '').strip()
                
                # First try to find the label element
                label_selectors = [
                    f"label:text-is('{clean_label}')",  # Exact match
                    f"label:text-is('{field_label}')",  # With asterisk if present
                    f"label:text-contains('{clean_label}')"  # Partial match
                ]
                
                label_element = None
                #for selector in label_selectors:
                try:
                    await self.page.get_by_label(clean_label).fill(value)
                    # label_element = await self.page.wait_for_selector(selector, timeout=timeout/3)
                    # if label_element:
                    #     break
                except Exception as e:
                    print(f"Error filling field '{field_label}': {e}")
                    continue
            
                # if label_element:
                #     # Get the 'for' attribute which links to the input's id
                #     for_attr = await label_element.get_attribute('for')
                #     if for_attr:
                #         # Find the input by its id
                #         input_element = await self.page.wait_for_selector(f"#{for_attr}", timeout=timeout)
                #         if input_element:
                #             await input_element.fill(value)
                #             results[field_label] = True
                #             continue
                
                # # If we couldn't find by label+for, try other methods
                # # Try by name that matches the cleaned label
                # clean_for_name = ''.join(c.lower() for c in clean_label if c.isalnum())
                # try:
                #     input_element = await self.page.wait_for_selector(f"input[name='{clean_for_name}'], input[name='name']", timeout=timeout/3)
                #     if input_element:
                #         await input_element.fill(value)
                #         results[field_label] = True
                #         continue
                # except Exception:
                #     pass
                
                # # Try by placeholder
                # try:
                #     input_element = await self.page.wait_for_selector(f"input[placeholder='{clean_label}']", timeout=timeout/3)
                #     if input_element:
                #         await input_element.fill(value)
                #         results[field_label] = True
                #         continue
                # except Exception:
                #     pass
                
                # # If all attempts failed
                # if field_label not in results:
                #     print(f"Could not find input field for label: '{field_label}'")
                #     results[field_label] = False
                    
            except Exception as e:
                print(f"Error filling field '{field_label}': {e}")
                results[field_label] = False
        
        return all(results.values())  # Return True only if all fields were successfully filled

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
        try:
            # Create a new event loop for the current thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            logging.info("Created new event loop for thread")
            return self.loop.run_until_complete(self.initialize())
        except Exception as e:
            error_details = traceback.format_exc()
            logging.error(f"Error initializing WebAutomation: {str(e)}\n{error_details}")
            raise
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
    
    def sync_click_and_switch_to_new_tab(self, selector: str) -> bool:
        """
        Synchronous wrapper for click_and_switch_to_new_tab.
        
        Args:
            selector (str): CSS selector of the element to click.
        
        Returns:
            bool: True if the click was successful, False otherwise.
        """
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.click_and_switch_to_new_tab(selector))
    
    def sync_scroll(self, direction: str = "down", amount: int = 500, smooth: bool = True) -> None:
        """Synchronous wrapper for scroll"""
        if not self.page:
            self.sync_initialize()
        return self.loop.run_until_complete(self.scroll(direction, amount, smooth))

# Example usage
if __name__ == "__main__":
    # Create an instance of the automation system
    automation = WebAutomation()
    
    try:
        # Initialize the browser
        automation.sync_initialize()
        
        # Navigate to a website
        automation.sync_navigate_to("https://www.tryfabricate.com/")
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
        
        automation.sync_click_and_switch_to_new_tab("a:has-text('Book a demo')")
        html_analysis = automation.sync_analyze_html_detailed()
        print("\nDetailed HTML Analysis:")
        print(f"Title: {html_analysis['title']}")
        print("\nMeta Tags:")
        for key, value in html_analysis['meta_tags'].items():
            print(f"- {key}: {value}")
        
        automation.sync_take_screenshot("example_screenshot.png")
        
        # Get clickable elements
        clickable_elements = automation.sync_get_clickable_elements()
        print(clickable_elements)
        print("\nClickable Elements:")
        for element in clickable_elements:
            print(f"- {element['tag']}: {element['text']}")
        
        
        
        # Example of scrolling
        automation.sync_scroll(direction="down", amount=500, smooth=True)
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