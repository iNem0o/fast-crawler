# Fast Crawler

Fast Crawler is a Fast API synchronous endpoint for extracting web content using Crawl4AI, with support for structured data extraction, browser automation, and advanced crawling features.

# Usage

```bash
docker run -d --name fast-crawler -p 8000:8000 -e API_TOKEN=your_secret_token ghcr.io/inem0o/fast-crawler:latest
```

```yml
  crawler-api:
    image: ghcr.io/inem0o/fast-crawler:latest
    ports:
      - target: 8000
        published: 8000
    environment:
      API_TOKEN: "your_secret_token"
```

You can access the swagger documentation here http://localhost:8000/docs

# Authentication

The API uses a static token-based authentication system. 
All requests must include this token in the headers to be authorized.

## API Token

The API token must be provided in the `X-Token` header for all requests:

```bash
curl -X POST "http://localhost:8000/crawl" \
     -H "X-Token: your_secret_token" \
     -H "Content-Type: application/json" \
     -d '{ ... }'
```

# /crawl Endpoint

## Overview

The `/crawl` endpoint is a POST endpoint that allows you to extract content from any web page. It provides extensive configuration options for browser behavior, content extraction, and page interactions.

Key features:
- Full browser automation with Chrome/Chromium
- Configurable viewport and network settings
- Advanced content extraction strategies
- Screenshot and PDF generation
- Cache management
- Structured data extraction without LLM

## Request Format

The request must be a POST request with a JSON body containing the following structure:

```json
{
    "url": "https://example.com",   // must be a valid HTTP/HTTPS URL.
    "browser": {                    // Browser settings (optional)
                                    // All settings have defaults
    },
    "config": {                     // Crawler settings (optional)
                                    // All settings have defaults
    }
}
```

### Required Headers
- `X-Token`: Your API authentication token
- `Content-Type`: Must be `application/json`

### URL Field
The `url` field 

### Browser Settings (Optional)

Control how the browser behaves during crawling:

```json
{
    "browser": {
        "viewport_width": 1920,
        "viewport_height": 1080,
        "proxy": "http://user:pass@proxy:8080",
        "proxy_config": {
            "server": "proxy:8080",
            "username": "user",
            "password": "pass"
        },
        "ignore_https_errors": true,
        "java_script_enabled": true,
        "use_persistent_context": false,
        "user_data_dir": "/path/to/user/data",
        "cookies": [
            {
                "name": "session",
                "value": "abc123",
                "url": "https://example.com"
            }
        ],
        "headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1"
        },
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) ...",
        "light_mode": false,
        "text_mode": false,
        "use_managed_browser": false,
        "extra_args": ["--disable-extensions", "--disable-gpu"]
    }
}
```

### Crawler Settings (Optional)

Control how the content is extracted and processed:

```json
{
    "config": {
        "extraction_schema": {
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
                }
            ]
        },
        "word_count_threshold": 200,
        "css_selector": "article.main-content",
        "excluded_selector": ".ads, .cookie-banner",
        "excluded_tags": ["script", "style", "nav"],
        "only_text": false,
        "prettiify": false,
        "keep_data_attributes": false,
        "remove_forms": false,
        "wait_until": "networkidle",
        "page_timeout": 30000,
        "screenshot": true,
        "pdf": false,
        "cache_mode": "enabled"
    }
}
```

## Response Format

The response is a JSON object with the following structure:

```json
{
    "url": "https://example.com",
    "result": {
        "success": true,
        "status_code": 200,
        "html": "...",
        "cleaned_html": "...",
        "markdown": "...",
        "text": "...",
        "title": "...",
        "description": "...",
        "media": {
            "images": [
                {
                    "src": "...",
                    "alt": "...",
                    "width": 800,
                    "height": 600
                }
            ]
        },
        "links": {
            "internal": [
                {
                    "href": "...",
                    "text": "..."
                }
            ],
            "external": []
        },
        "metadata": {},
        "headers": {},
        "screenshot": "base64...",  // If requested
        "pdf": "base64...",         // If requested
        "extracted_content": "..."   // If extraction_schema provided
    }
}
```

### Success Response Fields

- `url`: The URL that was crawled
- `result`: Object containing all extracted data
  - `success`: Boolean indicating if the crawl was successful
  - `status_code`: HTTP status code of the page
  - `html`: Original HTML content
  - `cleaned_html`: HTML after cleaning and processing
  - `markdown`: Content converted to markdown
  - `text`: Plain text content
  - `title`: Page title
  - `description`: Page meta description
  - `media`: Object containing found media (images, videos)
  - `links`: Object containing found links (internal/external)
  - `metadata`: Additional page metadata
  - `headers`: HTTP response headers
  - `screenshot`: Base64 encoded screenshot (if requested)
  - `pdf`: Base64 encoded PDF (if requested)
  - `extracted_content`: Structured data if extraction_schema was provided

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages:

### Authentication Errors (401)
```json
{
    "detail": "Invalid API token"
}
```

### Validation Errors (422)
```json
{
    "detail": [
        {
            "loc": ["body", "url"],
            "msg": "invalid or missing URL scheme",
            "type": "value_error.url.scheme"
        }
    ]
}
```

### Crawling Errors (500)
```json
{
    "detail": "Error crawling URL: timeout waiting for selector"
}
```


# Browser Settings

The browser settings control how the Chrome/Chromium browser instance behaves during crawling. These settings are all optional and have sensible defaults.

## Display Configuration

Configure the browser's viewport size:

```json
{
    "browser": {
        "viewport_width": 1920,
        "viewport_height": 1080
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `viewport_width` | integer | 1080 | Initial page width in pixels |
| `viewport_height` | integer | 600 | Initial page height in pixels |

## Network Configuration

Control how the browser handles network connections and security:

```json
{
    "browser": {
        "proxy": "http://user:pass@proxy:8080",
        "proxy_config": {
            "server": "proxy:8080",
            "username": "user",
            "password": "pass"
        },
        "ignore_https_errors": true,
        "headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1"
        },
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) ..."
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proxy` | string | null | Single-proxy URL for all traffic |
| `proxy_config` | object | null | Advanced proxy configuration |
| `ignore_https_errors` | boolean | true | Continue despite invalid SSL certificates |
| `headers` | object | null | Extra HTTP headers for all requests |
| `user_agent` | string | null | Custom User-Agent string |

## Browser Behavior

Control how the browser operates and maintains state:

```json
{
    "browser": {
        "java_script_enabled": true,
        "use_persistent_context": false,
        "user_data_dir": "/path/to/user/data",
        "cookies": [
            {
                "name": "session",
                "value": "abc123",
                "url": "https://example.com"
            }
        ]
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `java_script_enabled` | boolean | true | Enable/disable JavaScript execution |
| `use_persistent_context` | boolean | false | Maintain cookies/session between runs |
| `user_data_dir` | string | null | Directory for persistent data |
| `cookies` | array | null | Pre-set cookies for the session |

## Fixed Settings

Some browser settings are fixed and cannot be changed:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `headless` | true | Browser runs in headless mode |
| `browser_type` | "chromium" | Uses Chromium browser engine |

These settings ensure consistent behavior and optimal performance for web crawling.

# Crawler Settings

The crawler settings control how content is extracted, processed, and filtered during crawling. These settings are all optional and have sensible defaults.

## Content Processing

Configure how content is extracted and filtered:

```json
{
    "config": {
        "word_count_threshold": 200,
        "css_selector": "article.main-content",
        "excluded_selector": ".ads, .cookie-banner",
        "excluded_tags": ["script", "style", "nav"],
        "only_text": false,
        "prettiify": false,
        "keep_data_attributes": false,
        "remove_forms": false
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `word_count_threshold` | integer | 200 | Minimum words for text block inclusion |
| `css_selector` | string | null | CSS selector for content extraction |
| `excluded_selector` | string | null | CSS selector for content to remove |
| `excluded_tags` | array | null | HTML tags to remove |
| `only_text` | boolean | false | Extract text content only |
| `prettiify` | boolean | false | Beautify HTML output |
| `keep_data_attributes` | boolean | false | Preserve data-* attributes |
| `remove_forms` | boolean | false | Remove form elements |

## Page Navigation

Control page loading and timing:

```json
{
    "config": {
        "wait_until": "networkidle",
        "page_timeout": 30000,
        "wait_for": "css:.article-loaded",
        "wait_for_images": false,
        "delay_before_return_html": 0.5,
        "mean_delay": 0.2,
        "max_range": 0.5,
        "semaphore_count": 5
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `wait_until` | string | "domcontentloaded" | Navigation completion condition |
| `page_timeout` | integer | 60000 | Maximum time (ms) for page load |
| `wait_for` | string | null | CSS selector or JS condition |
| `wait_for_images` | boolean | false | Wait for images to load |
| `delay_before_return_html` | float | 0.1 | Additional delay before capture |
| `mean_delay` | float | 0.1 | Average delay between crawls |
| `max_range` | float | 0.3 | Maximum random delay variation |
| `semaphore_count` | integer | 5 | Maximum concurrent crawls |

## Page Interaction

Configure page interactions and dynamic content handling:

```json
{
    "config": {
        "js_code": [
            "document.querySelector('.cookie-accept')?.click()",
            "window.scrollTo(0, document.body.scrollHeight)"
        ],
        "js_only": false,
        "ignore_body_visibility": true,
        "scan_full_page": true,
        "scroll_delay": 0.5,
        "process_iframes": false,
        "remove_overlay_elements": false,
        "simulate_user": false,
        "override_navigator": false,
        "magic": false,
        "adjust_viewport_to_content": false
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `js_code` | string/array | null | JavaScript code to execute |
| `js_only` | boolean | false | Only execute JS without reload |
| `ignore_body_visibility` | boolean | true | Skip body visibility check |
| `scan_full_page` | boolean | false | Auto-scroll through page |
| `scroll_delay` | float | 0.2 | Delay between scroll steps |
| `process_iframes` | boolean | false | Extract iframe content |
| `remove_overlay_elements` | boolean | false | Remove modal overlays |
| `simulate_user` | boolean | false | Simulate user behavior |
| `override_navigator` | boolean | false | Override navigator properties |
| `magic` | boolean | false | Auto-handle common obstacles |
| `adjust_viewport_to_content` | boolean | false | Resize viewport to content |

## Media Handling

Configure screenshot, PDF, and image processing:

```json
{
    "config": {
        "screenshot": false,
        "screenshot_wait_for": 1.0,
        "screenshot_height_threshold": 20000,
        "pdf": false,
        "image_description_min_word_threshold": 50,
        "image_score_threshold": 3,
        "exclude_external_images": false
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `screenshot` | boolean | false | Capture page screenshot |
| `screenshot_wait_for` | float | null | Wait time before screenshot |
| `screenshot_height_threshold` | integer | 20000 | Max screenshot height |
| `pdf` | boolean | false | Generate PDF version |
| `image_description_min_word_threshold` | integer | 50 | Min words in image description |
| `image_score_threshold` | integer | 3 | Min image relevance score |
| `exclude_external_images` | boolean | false | Exclude external images |

## Link Processing

Configure link and domain handling:

```json
{
    "config": {
        "exclude_social_media_domains": false,
        "exclude_external_links": false,
        "exclude_social_media_links": false,
        "exclude_domains": ["ads.example.com", "analytics.com"]
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `exclude_social_media_domains` | boolean | false | Remove social media domains |
| `exclude_external_links` | boolean | false | Remove external links |
| `exclude_social_media_links` | boolean | false | Remove social sharing links |
| `exclude_domains` | array | null | Domains to exclude |

## Cache Management

Control caching behavior:

```json
{
    "config": {
        "cache_mode": "enabled",
        "session_id": "session_123",
        "bypass_cache": false,
        "disable_cache": false,
        "no_cache_read": false,
        "no_cache_write": false
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_mode` | string | "enabled" | Cache control mode |
| `session_id` | string | null | Browser session identifier |
| `bypass_cache` | boolean | false | Ignore but update cache |
| `disable_cache` | boolean | false | Disable caching completely |
| `no_cache_read` | boolean | false | Only write to cache |
| `no_cache_write` | boolean | false | Only read from cache |

## Debug & Logging

Configure debugging options:

```json
{
    "config": {
        "verbose": true,
        "log_console": false
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verbose` | boolean | true | Enable detailed logging |
| `log_console` | boolean | false | Log browser console output |

# Content Extraction Strategies

The API offers several content extraction strategies to meet different needs.

## Basic Content Extraction

The API provides three basic formats for content extraction:

```json
{
    "config": {
        "only_text": false,
        "prettiify": false,
        "keep_data_attributes": false
    }
}
```

| Format | Description | Configuration |
|--------|-------------|---------------|
| Full HTML | Complete original HTML | Default parameters |
| Clean HTML | Cleaned and formatted HTML | `prettiify: true` |
| Text Only | Raw text without HTML | `only_text: true` |

### Content Filtering

Control extracted content with these options:

```json
{
    "config": {
        "word_count_threshold": 200,
        "css_selector": "article.main-content",
        "excluded_selector": ".ads, .cookie-banner",
        "excluded_tags": ["script", "style", "nav"],
        "remove_forms": false
    }
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `word_count_threshold` | integer | 200 | Minimum words for text block inclusion |
| `css_selector` | string | null | CSS selector for content extraction |
| `excluded_selector` | string | null | CSS selector for content to remove |
| `excluded_tags` | array | null | HTML tags to remove |
| `remove_forms` | boolean | false | Remove form elements |

## JSON/CSS Extraction Schema

The extraction schema allows structured data extraction without LLM.

### Schema Structure

```json
{
    "config": {
        "extraction_schema": {
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
                }
            ]
        }
    }
}
```

### Field Types

| Type | Description | Example |
|------|-------------|---------|
| `text` | Extract text content | `{"type": "text"}` |
| `html` | Extract HTML content | `{"type": "html"}` |
| `attribute` | Extract a specific attribute | `{"type": "attribute", "attribute": "src"}` |
| `nested` | Extract a nested object | `{"type": "nested", "fields": [...]}` |
| `list` | Extract a list of simple values | `{"type": "list"}` |
| `nested_list` | Extract a list of complex objects | `{"type": "nested_list", "fields": [...]}` |

### Complete Example

```json
{
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
```