import re
import requests
from markdownify import markdownify
from requests.exceptions import RequestException
from smolagents import tool
from urllib.parse import urlparse

@tool
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.
    If the URL is a Wikipedia page, it uses Wikipedia's REST API for a cleaner summary.
    
    Args:
        url: The URL of the webpage to visit.
        
    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    try:
        headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Check if the URL is a Wikipedia article
        parsed_url = urlparse(url)
        if parsed_url.netloc.endswith("wikipedia.org") and parsed_url.path.startswith("/wiki/"):
            # Extract the language prefix and article title
            lang = parsed_url.netloc.split('.')[0]
            title = parsed_url.path.split("/wiki/", 1)[-1]
            
            # Use Wikipedia's REST API to get a clean summary
            api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
            api_response = requests.get(api_url, headers=headers, timeout=10)
            
            if api_response.status_code == 200:
                data = api_response.json()
                if "extract" in data:
                    return data["extract"]

        # Default fallback for non-Wikipedia URLs or if the API failed but we still want to try scraping
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        markdown_content = markdownify(response.text).strip()
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
        return markdown_content
    except RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

if __name__ == "__main__":
    # Test Wikipedia article (should return clean plain-text extract)
    print("--- Wikipedia Test ---")
    print(visit_webpage("https://en.wikipedia.org/wiki/Hugging_Face"))
    
    # Test normal webpage
    print("\n--- Normal Webpage Test ---")
    print(visit_webpage("https://example.com")[:200])
