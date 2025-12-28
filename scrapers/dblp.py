from typing import List, Optional
import httpx
import xml.etree.ElementTree as ET
from utils import calculate_confidence_score


async def scrape_dblp(
    first_name: str,
    last_name: str,
    institution: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> List[dict]:
    """
    Scrape dblp Computer Science Bibliography
    API Docs: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
    """
    results = []
    full_name = f"{first_name} {last_name}"
    
    try:
        print(f"Searching dblp for: {full_name}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = "https://dblp.org/search/author/api"
            params = {
                "q": full_name,
                "format": "json",
                "h": 10
            }
            
            response = await client.get(search_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                hits = data.get('result', {}).get('hits', {}).get('hit', [])
                
                for hit in hits[:3]:
                    info = hit.get('info', {})
                    author_name = info.get('author', '')
                    author_url = info.get('url', '')
                    
                    print(f"Found dblp author: {author_name}")
                    
                    if last_name.lower() not in author_name.lower():
                        continue
                    
                    if author_url:
                        pub_response = await client.get(f"{author_url}.xml")
                        
                        if pub_response.status_code == 200:
                            root = ET.fromstring(pub_response.content)
                            
                            pubs = []
                            for pub_type in ['article', 'inproceedings', 'proceedings', 'book', 'incollection']:
                                pubs.extend(root.findall(f".//{pub_type}"))
                            
                            pubs_with_year = []
                            for pub in pubs:
                                year_elem = pub.find('year')
                                year = int(year_elem.text) if year_elem is not None and year_elem.text else 0
                                pubs_with_year.append((year, pub))
                            
                            pubs_with_year.sort(reverse=True, key=lambda x: x[0])
                            
                            for year, pub in pubs_with_year[:5]:
                                try:
                                    title_elem = pub.find('title')
                                    title = title_elem.text if title_elem is not None else "No title"
                                    
                                    authors = []
                                    for author_elem in pub.findall('author'):
                                        if author_elem.text:
                                            authors.append(author_elem.text)
                                    authors_str = ', '.join(authors)
                                    
                                    venue = None
                                    for venue_tag in ['journal', 'booktitle', 'publisher']:
                                        venue_elem = pub.find(venue_tag)
                                        if venue_elem is not None and venue_elem.text:
                                            venue = venue_elem.text
                                            break
                                    
                                    ee_elem = pub.find('ee')
                                    url = ee_elem.text if ee_elem is not None else ""
                                    
                                    confidence = calculate_confidence_score(
                                        authors_str,
                                        full_name,
                                        scraped_institution=None,
                                        target_institution=institution,
                                        scraped_text=f"{title} {authors_str} {venue or ''}",
                                        field_of_study=field_of_study
                                    )
                                    
                                    results.append({
                                        'source': 'dblp',
                                        'url': url or f"https://dblp.org/search?q={title.replace(' ', '+')}",
                                        'title': title,
                                        'description': f"Published in {venue or 'unknown venue'} ({year})",
                                        'authors': authors_str,
                                        'confidenceScore': confidence,
                                        'raw_data': {
                                            'full_authors': authors_str,
                                            'venue': venue,
                                            'year': year,
                                            'type': pub.tag
                                        }
                                    })
                                    
                                except Exception as pub_error:
                                    print(f"Error processing dblp publication: {pub_error}")
                                    continue
                            
                            if results:
                                break
        
        print(f"Found {len(results)} results from dblp")
        
    except Exception as e:
        print(f"Error scraping dblp: {e}")
    
    return results
