from typing import List, Optional
import httpx
import xml.etree.ElementTree as ET
from utils import calculate_confidence_score


async def scrape_arxiv(
    first_name: str,
    last_name: str,
    institution: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> List[dict]:
    """
    Scrape arXiv for preprints
    API Docs: https://info.arxiv.org/help/api/index.html
    """
    results = []
    full_name = f"{first_name} {last_name}"
    
    try:
        print(f"Searching arXiv for: {full_name}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"au:{full_name}",
                "start": 0,
                "max_results": 5,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            response = await client.get(search_url, params=params)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                entries = root.findall('atom:entry', ns)
                
                for entry in entries:
                    try:
                        title_elem = entry.find('atom:title', ns)
                        title = title_elem.text.strip() if title_elem is not None else "No title"
                        
                        summary_elem = entry.find('atom:summary', ns)
                        summary = summary_elem.text.strip() if summary_elem is not None else ""
                        
                        authors = []
                        for author_elem in entry.findall('atom:author', ns):
                            name_elem = author_elem.find('atom:name', ns)
                            if name_elem is not None and name_elem.text:
                                authors.append(name_elem.text)
                        authors_str = ', '.join(authors)
                        
                        link_elem = entry.find("atom:link[@title='pdf']", ns)
                        if link_elem is None:
                            link_elem = entry.find('atom:link', ns)
                        url = link_elem.get('href') if link_elem is not None else ""
                        
                        published_elem = entry.find('atom:published', ns)
                        published = published_elem.text[:4] if published_elem is not None else ""
                        
                        categories = []
                        for cat_elem in entry.findall('atom:category', ns):
                            term = cat_elem.get('term')
                            if term:
                                categories.append(term)
                        
                        confidence = calculate_confidence_score(
                            authors_str,
                            full_name,
                            scraped_institution=None,
                            target_institution=institution,
                            scraped_text=f"{title} {summary} {authors_str}",
                            field_of_study=field_of_study
                        )
                        
                        results.append({
                            'source': 'arXiv',
                            'url': url,
                            'title': title,
                            'description': summary[:500],
                            'authors': authors_str,
                            'confidenceScore': confidence,
                            'raw_data': {
                                'full_authors': authors_str,
                                'abstract': summary,
                                'year': published,
                                'categories': categories
                            }
                        })
                        
                    except Exception as entry_error:
                        print(f"Error processing arXiv entry: {entry_error}")
                        continue
        
        print(f"Found {len(results)} results from arXiv")
        
    except Exception as e:
        print(f"Error scraping arXiv: {e}")
    
    return results
