from typing import List, Optional
import httpx
from utils import calculate_confidence_score


async def scrape_semantic_scholar(
    first_name: str,
    last_name: str,
    institution: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> List[dict]:
    """
    Scrape Semantic Scholar using their free API
    API Docs: https://api.semanticscholar.org/
    Note: Free tier has rate limits but no API key needed for basic usage
    """
    results = []
    full_name = f"{first_name} {last_name}"
    
    try:
        print(f"Searching Semantic Scholar for: {full_name}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = "https://api.semanticscholar.org/graph/v1/author/search"
            params = {
                "query": full_name,
                "limit": 3
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Academic Research Bot)"
            }
            
            response = await client.get(search_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                authors = data.get('data', [])
                
                for author in authors:
                    author_name = author.get('name', '')
                    author_id = author.get('authorId', '')
                    
                    print(f"Found Semantic Scholar author: {author_name}")
                    
                    if last_name.lower() not in author_name.lower():
                        continue
                    
                    if author_id:
                        papers_url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers"
                        papers_params = {
                            "limit": 5,
                            "fields": "title,authors,year,abstract,url,venue,citationCount"
                        }
                        
                        papers_response = await client.get(papers_url, params=papers_params, headers=headers)
                        
                        if papers_response.status_code == 200:
                            papers_data = papers_response.json()
                            papers = papers_data.get('data', [])
                            
                            for paper in papers:
                                try:
                                    title = paper.get('title', 'No title')
                                    abstract = paper.get('abstract', '')
                                    year = paper.get('year', '')
                                    url = paper.get('url', '')
                                    venue = paper.get('venue', '')
                                    citation_count = paper.get('citationCount', 0)
                                    
                                    authors_list = paper.get('authors', [])
                                    authors_str = ', '.join([a.get('name', '') for a in authors_list])
                                    
                                    confidence = calculate_confidence_score(
                                        authors_str,
                                        full_name,
                                        scraped_institution=None,
                                        target_institution=institution,
                                        scraped_text=f"{title} {abstract} {authors_str} {venue}",
                                        field_of_study=field_of_study
                                    )
                                    
                                    results.append({
                                        'source': 'Semantic Scholar',
                                        'url': url or f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                                        'title': title,
                                        'description': abstract[:500] if abstract else f"Published in {venue} ({year})",
                                        'authors': authors_str,
                                        'confidenceScore': confidence,
                                        'raw_data': {
                                            'full_authors': authors_str,
                                            'abstract': abstract,
                                            'venue': venue,
                                            'year': year,
                                            'citation_count': citation_count
                                        }
                                    })
                                    
                                except Exception as paper_error:
                                    print(f"Error processing Semantic Scholar paper: {paper_error}")
                                    continue
                            
                            if results:
                                break
        
        print(f"Found {len(results)} results from Semantic Scholar")
        
    except Exception as e:
        print(f"Error scraping Semantic Scholar: {e}")
    
    return results
