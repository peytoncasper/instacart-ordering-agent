from crewai import Agent, Task, LLM
from crewai.tools import BaseTool
from litellm import completion
import json
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from typing import Optional, Any
from pydantic import Field
from bs4 import BeautifulSoup
from html_utils import clean_html_file  # Import the function

# Load environment variables
load_dotenv()

# Load Vertex AI credentials
with open(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'), 'r') as file:
    vertex_credentials = json.load(file)
vertex_credentials_json = json.dumps(vertex_credentials)

llm = LLM(
    model="gemini-2.0-flash-exp",
    custom_llm_provider="vertex_ai",
    api_key=vertex_credentials_json
)
# Custom Playwright Tools
class OpenBrowserTool(BaseTool):
    name: str = "open_browser"
    description: str = "Opens a new browser instance. Specify browser_type as 'chromium', 'firefox', or 'webkit'"
    playwright: Optional[Any] = Field(default=None)
    browser: Optional[Any] = Field(default=None)
    page: Optional[Any] = Field(default=None)
    
    def __init__(self):
        super().__init__()
    
    def _run(self, browser_type: str = 'chromium') -> str:
        """Opens a new browser instance"""
        self.playwright = sync_playwright().start()
        if browser_type == 'chromium':
            self.browser = self.playwright.chromium.launch(headless=False)
        elif browser_type == 'firefox':
            self.browser = self.playwright.firefox.launch(headless=False)
        elif browser_type == 'webkit':
            self.browser = self.playwright.webkit.launch(headless=False)
        self.page = self.browser.new_page()
        return "Browser opened successfully"

class NavigateTool(BaseTool):
    name: str = "navigate"
    description: str = "Navigates to a specified URL in the opened browser"
    browser_tool: OpenBrowserTool = Field(default=None)
    
    def __init__(self, browser_tool: OpenBrowserTool):
        super().__init__(browser_tool=browser_tool)
    
    def _run(self, url: str) -> str:
        """Navigates to a specified URL"""
        if not self.browser_tool.page:
            return "Browser is not opened. Please open browser first."
        self.browser_tool.page.goto(url)
        return f"Navigated to {url} successfully"

class GetHtmlTool(BaseTool):
    name: str = "get_html"
    description: str = "Gets the HTML from the current page and cleans it using clean_html_file"
    browser_tool: OpenBrowserTool = Field(default=None)
    
    def __init__(self, browser_tool: OpenBrowserTool):
        super().__init__(browser_tool=browser_tool)
    
    def _run(self, file_path: str) -> str:
        """Gets the HTML from the current page and cleans it"""
        if not self.browser_tool.page:
            return "Browser is not opened. Please open browser first."
        
        # Get the HTML content from the page
        html_content = self.browser_tool.page.content()
        
        # Write the HTML content to a file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Clean the HTML file
        clean_html_file(file_path)
        
        return f"HTML content retrieved and cleaned. Saved to {file_path}"

class SaveHtmlTool(BaseTool):
    name: str = "save_html"
    description: str = "Saves the HTML content to a specified file path"
    browser_tool: OpenBrowserTool = Field(default=None)
    
    def __init__(self, browser_tool: OpenBrowserTool):
        super().__init__(browser_tool=browser_tool)
    
    def _run(self, file_path: str) -> str:
        """Saves the HTML content to a specified file path"""
        if not self.browser_tool.page:
            return "Browser is not opened. Please open browser first."
        
        # Get the HTML content from the page
        html_content = self.browser_tool.page.content()
        
        # Write the HTML content to a file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(clean_html_file(html_content))
        
        return f"HTML content saved to {file_path}"

# Initialize tools
browser_tool = OpenBrowserTool()
navigate_tool = NavigateTool(browser_tool)
get_html_tool = GetHtmlTool(browser_tool)
save_html_tool = SaveHtmlTool(browser_tool)

# Create a web automation agent
web_agent = Agent(
    role='Web Navigator',
    goal='Navigate and interact with web pages',
    backstory="""You are a web automation expert capable of browsing websites 
    and gathering information. You can open browsers and navigate to different URLs.""",
    tools=[browser_tool, navigate_tool, get_html_tool, save_html_tool],
    llm=llm  # Use the new GeminiLLM instance
)

web_task = Task(
    description="Open a browser and navigate to 'https://www.instacart.com'",
    expected_output="Confirmation of successful browser opening and navigation and save the file to index.html",
    agent=web_agent
)

# Test the agent with the task
print("\nWeb Agent's Response:")
web_result = web_agent.execute_task(web_task)
print(web_result)
