import os
from typing import Optional, Dict, Any, List, Union, Literal
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, HttpUrl, Field, conint
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlResult
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# Load environment variables
load_dotenv()

# Get API token from environment
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is not set")

app = FastAPI(
    title="Fast Crawler API",
    description="API for extracting web content using Crawl4AI",
    version="1.0.0"
)

class BrowserSettings(BaseModel):
    """
    Browser configuration settings for controlling how the browser behaves during crawling.
    Note: headless mode and browser type are fixed and cannot be changed.
    """
    
    # Display settings
    viewport_width: Optional[int] = Field(
        default=1080,
        description="Initial page width in pixels. Useful for testing responsive layouts or ensuring specific viewport sizes.",
        example=1920,
        ge=0
    )
    viewport_height: Optional[int] = Field(
        default=600,
        description="Initial page height in pixels. Important for capturing full-page content.",
        example=1080,
        ge=0
    )
    
    # Network settings
    proxy: Optional[str] = Field(
        default=None,
        description="""Single-proxy URL for all traffic. Format: 'protocol://[user:pass@]host:port'.
        Example: 'http://user:pass@proxy:8080' or 'socks5://proxy:1080'""",
        example="http://user:pass@proxy:8080"
    )
    proxy_config: Optional[Dict[str, str]] = Field(
        default=None,
        description="""Advanced proxy configuration for complex setups.
        Example: {"server": "proxy:8080", "username": "user", "password": "pass"}""",
        example={"server": "proxy:8080", "username": "user", "password": "pass"}
    )
    ignore_https_errors: Optional[bool] = Field(
        default=True,
        description="If True, continues despite invalid SSL certificates. Useful for development or testing environments."
    )
    
    # Browser behavior
    java_script_enabled: Optional[bool] = Field(
        default=True,
        description="Enable/disable JavaScript. Disable for static content only or better performance."
    )
    use_persistent_context: Optional[bool] = Field(
        default=False,
        description="""If True, maintains cookies and session data between runs.
        Must set user_data_dir if enabled. Automatically sets use_managed_browser=True."""
    )
    user_data_dir: Optional[str] = Field(
        default=None,
        description="Directory to store persistent data (cookies, cache). Required if use_persistent_context=True.",
        example="/path/to/user/data"
    )
    
    # Headers and identity
    cookies: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="""Pre-set cookies for the browser session.
        Example: [{"name": "session", "value": "abc123", "url": "https://example.com"}]""",
        example=[{
            "name": "session",
            "value": "abc123",
            "url": "https://example.com"
        }]
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="""Extra HTTP headers for all requests.
        Example: {"Accept-Language": "en-US,en;q=0.9", "DNT": "1"}""",
        example={"Accept-Language": "en-US,en;q=0.9", "DNT": "1"}
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="""Custom User-Agent string. Useful for mimicking specific browsers or devices.""",
        example="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36"
    )
    
    # Performance options
    light_mode: Optional[bool] = Field(
        default=False,
        description="Disables some background features for better performance. Good for basic content extraction."
    )
    text_mode: Optional[bool] = Field(
        default=False,
        description="Disables images and heavy content loading for faster crawling. Best for text-only extraction."
    )
    use_managed_browser: Optional[bool] = Field(
        default=False,
        description="For advanced browser control. Auto-enabled with persistent context. Useful for debugging."
    )
    extra_args: Optional[List[str]] = Field(
        default=None,
        description="""Additional Chrome flags for the browser process.
        Example: ["--disable-extensions", "--disable-gpu"]""",
        example=["--disable-extensions", "--disable-gpu"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "viewport_width": 1920,
                "viewport_height": 1080,
                "proxy": "http://user:pass@proxy:8080",
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36",
                "text_mode": True,
                "ignore_https_errors": True,
                "headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "DNT": "1"
                }
            }
        }

class ExtractionField(BaseModel):
    """
    Definition of a field to extract in the JSON/CSS extraction strategy.
    """
    name: str = Field(..., description="Field name in the resulting JSON")
    selector: Optional[str] = Field(None, description="CSS selector to find the element")
    type: str = Field(..., description="""Extraction type:
        - text: Extract element's text content
        - html: Extract element's HTML content
        - attribute: Extract a specific attribute
        - nested: A single sub-object
        - list: List of simple values
        - nested_list: List of complex objects""")
    attribute: Optional[str] = Field(None, description="Attribute name to extract if type='attribute'")
    default: Optional[Any] = Field(None, description="Default value if nothing is found")
    fields: Optional[List['ExtractionField']] = Field(None, description="Sub-fields for nested/list/nested_list types")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "price",
                "selector": "span.price",
                "type": "text",
                "default": "0"
            }
        }

class ExtractionSchema(BaseModel):
    """
    Complete schema for JSON/CSS extraction.
    """
    name: str = Field(..., description="Name of the extraction schema")
    baseSelector: str = Field(..., description="CSS selector for the main container element")
    baseFields: Optional[List[ExtractionField]] = Field(None, description="Fields to extract from the container element")
    fields: List[ExtractionField] = Field(..., description="List of fields to extract")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Product List",
                "baseSelector": "div.product-card",
                "baseFields": [
                    {
                        "name": "product_id",
                        "type": "attribute",
                        "attribute": "data-product-id"
                    }
                ],
                "fields": [
                    {
                        "name": "title",
                        "selector": "h2.product-title",
                        "type": "text"
                    },
                    {
                        "name": "price",
                        "selector": "span.price",
                        "type": "text"
                    },
                    {
                        "name": "details",
                        "selector": "div.product-details",
                        "type": "nested",
                        "fields": [
                            {
                                "name": "brand",
                                "selector": "span.brand",
                                "type": "text"
                            },
                            {
                                "name": "model",
                                "selector": "span.model",
                                "type": "text"
                            }
                        ]
                    },
                    {
                        "name": "features",
                        "selector": "ul.features li",
                        "type": "list",
                        "fields": [
                            {
                                "name": "feature",
                                "type": "text"
                            }
                        ]
                    }
                ]
            }
        }

# Référence circulaire pour les sous-champs
ExtractionField.update_forward_refs()

class CrawlerConfig(BaseModel):
    """
    Configuration for each crawl operation, controlling content extraction, navigation,
    page interactions, media handling, and more. Each parameter is designed to fine-tune
    how the crawler behaves when processing a specific URL.
    """

    # Extraction Strategy
    extraction_schema: Optional[ExtractionSchema] = Field(
        default=None,
        description="JSON/CSS extraction schema for structured data extraction without LLM"
    )

    # Content Processing
    word_count_threshold: Optional[int] = Field(
        default=200,
        description="""Minimum number of words for a text block to be included.
        Helps filter out trivial content like footers or navigation.""",
        example=100,
        ge=0
    )
    css_selector: Optional[str] = Field(
        default=None,
        description="""CSS selector to extract specific content. Only content matching this selector will be kept.
        Example: 'article.main-content' or 'div#article-body'""",
        example="article.main-content"
    )
    excluded_tags: Optional[List[str]] = Field(
        default=None,
        description="""HTML tags to remove from the final content.
        Common tags to exclude: navigation, scripts, styles, ads.""",
        example=["nav", "script", "style", "footer", "aside"]
    )
    excluded_selector: Optional[str] = Field(
        default=None,
        description="""CSS selector for elements to exclude. Multiple selectors can be comma-separated.
        Example: '.ads, .social-share, #cookie-banner'""",
        example=".ads, .cookie-notice, .newsletter-signup"
    )
    only_text: Optional[bool] = Field(
        default=False,
        description="Extract text content only, stripping all HTML formatting. Useful for pure text analysis."
    )
    prettiify: Optional[bool] = Field(
        default=False,
        description="Beautify the final HTML output. Makes it more readable but slower to process."
    )
    keep_data_attributes: Optional[bool] = Field(
        default=False,
        description="Preserve data-* attributes in the cleaned HTML. Useful for maintaining custom data attributes."
    )
    remove_forms: Optional[bool] = Field(
        default=False,
        description="Remove all <form> elements from the output. Helpful for cleaning up interactive elements."
    )

    # Page Navigation & Timing
    wait_until: Optional[str] = Field(
        default="domcontentloaded",
        description="""When to consider navigation complete:
        - 'domcontentloaded': Basic HTML loaded
        - 'load': All resources (images, styles) loaded
        - 'networkidle': No network activity for 500ms""",
        example="networkidle"
    )
    page_timeout: Optional[int] = Field(
        default=60000,
        description="Maximum time (in milliseconds) to wait for page load or JavaScript execution",
        example=30000,
        ge=0
    )
    wait_for: Optional[str] = Field(
        default=None,
        description="""Wait for specific element or condition before proceeding:
        - CSS selector: 'css:.loaded-indicator'
        - JavaScript: 'js:() => document.querySelector(".content")?.dataset.loaded === "true"'""",
        example="css:.article-loaded"
    )
    wait_for_images: Optional[bool] = Field(
        default=False,
        description="Wait for all images to load before proceeding. Important for visual content extraction."
    )
    delay_before_return_html: Optional[float] = Field(
        default=0.1,
        description="Additional delay (in seconds) before capturing final HTML. Helps with last-moment updates.",
        example=0.5,
        ge=0
    )
    mean_delay: Optional[float] = Field(
        default=0.1,
        description="Average delay between multiple crawls to avoid overwhelming servers",
        example=0.2,
        ge=0
    )
    max_range: Optional[float] = Field(
        default=0.3,
        description="Maximum random delay variation for multiple crawls",
        example=0.5,
        ge=0
    )
    semaphore_count: Optional[int] = Field(
        default=5,
        description="Maximum number of concurrent crawls when using arun_many()",
        example=10,
        ge=1
    )

    # Page Interaction
    js_code: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="""JavaScript code to execute after page load.
        Can be a single string or list of commands to execute in sequence.""",
        example=[
            "document.querySelector('.cookie-accept')?.click()",
            "window.scrollTo(0, document.body.scrollHeight)"
        ]
    )
    js_only: Optional[bool] = Field(
        default=False,
        description="""Only execute JavaScript without reloading the page.
        Requires session_id for maintaining browser context."""
    )
    ignore_body_visibility: Optional[bool] = Field(
        default=True,
        description="Skip checking if <body> is visible. Usually best left enabled."
    )
    scan_full_page: Optional[bool] = Field(
        default=False,
        description="Automatically scroll through the entire page to load lazy content."
    )
    scroll_delay: Optional[float] = Field(
        default=0.2,
        description="Delay (in seconds) between scroll steps when scan_full_page is true",
        example=0.5,
        ge=0
    )
    process_iframes: Optional[bool] = Field(
        default=False,
        description="Extract and inline content from iframes into the main document."
    )
    remove_overlay_elements: Optional[bool] = Field(
        default=False,
        description="Attempt to remove modal overlays and popups that might block content."
    )
    simulate_user: Optional[bool] = Field(
        default=False,
        description="Simulate realistic user behavior (mouse movements, delays) to avoid bot detection."
    )
    override_navigator: Optional[bool] = Field(
        default=False,
        description="Override navigator properties in JavaScript for better stealth."
    )
    magic: Optional[bool] = Field(
        default=False,
        description="Experimental: Automatically handle common obstacles like cookie notices and popups."
    )
    adjust_viewport_to_content: Optional[bool] = Field(
        default=False,
        description="Automatically resize viewport to match content height. Useful for full-page captures."
    )

    # Media Handling
    screenshot: Optional[bool] = Field(
        default=False,
        description="Capture a screenshot of the page (returned as base64 string)."
    )
    screenshot_wait_for: Optional[float] = Field(
        default=None,
        description="Additional wait time (in seconds) before taking screenshot",
        example=1.0,
        ge=0
    )
    screenshot_height_threshold: Optional[int] = Field(
        default=20000,
        description="Maximum height (in pixels) for normal screenshot capture",
        example=15000,
        ge=0
    )
    pdf: Optional[bool] = Field(
        default=False,
        description="Generate a PDF version of the page."
    )
    image_description_min_word_threshold: Optional[int] = Field(
        default=50,
        description="Minimum words required in image alt text or description to be considered valid",
        example=30,
        ge=0
    )
    image_score_threshold: Optional[int] = Field(
        default=3,
        description="Minimum relevance score for including images (based on size, position, etc)",
        example=5,
        ge=0
    )
    exclude_external_images: Optional[bool] = Field(
        default=False,
        description="Exclude images hosted on external domains."
    )

    # Link/Domain Handling
    exclude_social_media_domains: Optional[bool] = Field(
        default=False,
        description="Remove links to common social media platforms (Facebook, Twitter, etc)."
    )
    exclude_external_links: Optional[bool] = Field(
        default=False,
        description="Remove all links that point outside the current domain."
    )
    exclude_social_media_links: Optional[bool] = Field(
        default=False,
        description="Remove social media sharing and profile links."
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None,
        description="List of domains to exclude from link extraction",
        example=["ads.example.com", "analytics.com", "tracker.com"]
    )

    # Session & Cache
    cache_mode: Optional[str] = Field(
        default="enabled",
        description="""Cache control mode:
        - enabled: Use cache normally
        - disabled: Don't use cache
        - bypass: Ignore but update cache
        - write_only: Only write to cache
        - read_only: Only read from cache""",
        example="enabled"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Unique identifier to reuse the same browser session across calls",
        example="session_123"
    )
    bypass_cache: Optional[bool] = Field(
        default=False,
        description="Shorthand for cache_mode='bypass'. Ignores cache but updates it."
    )
    disable_cache: Optional[bool] = Field(
        default=False,
        description="Shorthand for cache_mode='disabled'. Completely disables caching."
    )
    no_cache_read: Optional[bool] = Field(
        default=False,
        description="Shorthand for cache_mode='write_only'. Only writes to cache."
    )
    no_cache_write: Optional[bool] = Field(
        default=False,
        description="Shorthand for cache_mode='read_only'. Only reads from cache."
    )

    # Debug & Logging
    verbose: Optional[bool] = Field(
        default=True,
        description="Enable detailed logging of crawl operations and steps."
    )
    log_console: Optional[bool] = Field(
        default=False,
        description="Log browser console output for debugging JavaScript issues."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "css_selector": "article.main-content",
                "excluded_tags": ["script", "style", "nav", "footer"],
                "wait_until": "networkidle",
                "page_timeout": 30000,
                "scan_full_page": True,
                "screenshot": True,
                "magic": True,
                "cache_mode": "enabled",
                "exclude_social_media_links": True,
                "verbose": True
            }
        }

class URLInput(BaseModel):
    url: HttpUrl
    browser: Optional[BrowserSettings] = Field(default_factory=BrowserSettings, description="Browser configuration options")
    config: Optional[CrawlerConfig] = Field(default_factory=CrawlerConfig, description="Crawler configuration options")

class CrawlResponse(BaseModel):
    url: HttpUrl
    result: Dict[str, Any]

async def verify_token(x_token: str = Header(...)):
    if x_token != API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid API token"
        )
    return x_token

@app.post("/crawl", response_model=CrawlResponse)
async def crawl_url(url_input: URLInput, token: str = Depends(verify_token)):
    try:
        # Convert browser settings to BrowserConfig
        browser_dict = url_input.browser.model_dump(exclude_none=True)
        browser_config = BrowserConfig(
            headless=True,  # Fixed value
            browser_type="chromium",  # Fixed value
            verbose=True,
            **browser_dict
        )
        
        # Convert crawler config to CrawlerRunConfig
        config_dict = url_input.config.model_dump(exclude_none=True)

        # Handle extraction strategy if provided
        if "extraction_schema" in config_dict:
            schema = config_dict.pop("extraction_schema")
            config_dict["extraction_strategy"] = JsonCssExtractionStrategy(
                schema=schema,
                verbose=True
            )

        run_config = CrawlerRunConfig(**config_dict)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=str(url_input.url),
                config=run_config
            )
            
            return CrawlResponse(
                url=url_input.url,
                result=result.__dict__
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error crawling URL: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
