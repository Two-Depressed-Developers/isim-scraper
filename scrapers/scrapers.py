"""
Scrapers for Computer Science publications
- dblp: Computer Science Bibliography
- arXiv: Preprints
- Semantic Scholar: Academic papers with free API
"""
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