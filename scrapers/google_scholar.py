from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
from utils import calculate_confidence_score


async def scrape_google_scholar(
    first_name: str,
    last_name: str,
    institution: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> List[dict]:
    results = []
    full_name = f"{first_name} {last_name}"

    print(f"Searching Google Scholar for: {full_name}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = f"https://scholar.google.com/scholar?q={full_name.replace(' ', '+')}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = await client.get(search_url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                publications = soup.find_all('div', class_='gs_ri')[:5]
                
                for pub in publications:
                    title_elem = pub.find('h3', class_='gs_rt')
                    snippet_elem = pub.find('div', class_='gs_rs')
                    
                    if title_elem:
                        title = title_elem.get_text()
                        snippet = snippet_elem.get_text() if snippet_elem else ""
                        link = title_elem.find('a')
                        url = link['href'] if link and link.get('href') else search_url
                        
                        authors_elem = pub.find('div', class_='gs_a')
                        authors = authors_elem.get_text() if authors_elem else ""
                        
                        scraped_institution = None
                        if authors_elem:
                            parts = authors.split('-')
                            if len(parts) > 1:
                                scraped_institution = parts[1].strip()
                        
                        scraped_text = f"{title} {snippet} {authors}"
                        confidence = calculate_confidence_score(
                            authors,
                            full_name,
                            scraped_institution=scraped_institution,
                            target_institution=institution,
                            scraped_text=scraped_text,
                            field_of_study=field_of_study
                        )
                        
                        results.append({
                            'source': 'Google Scholar',
                            'url': url,
                            'title': title,
                            'description': snippet,
                            'authors': authors,
                            'confidenceScore': confidence,
                            'raw_data': {
                                'full_authors': authors,
                                'snippet': snippet
                            }
                        })

        print(f"Found {len(results)} results from Google Scholar")
            
    except Exception as e:
        print(f"Error scraping Google Scholar: {e}")
    
    return results
