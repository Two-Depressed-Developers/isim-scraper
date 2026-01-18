from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
from utils import fetch_with_retry


async def scrape_researchgate(
    first_name: str,
    last_name: str,
    institution: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> List[dict]:
    results = []
    full_name = f"{first_name} {last_name}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = f"https://www.researchgate.net/search/researcher?q={full_name.replace(' ', '%20')}"
            
            response = await fetch_with_retry(client, search_url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                pass
                    
    except Exception as e:
        print(f"Error scraping ResearchGate: {e}")
    
    return results
