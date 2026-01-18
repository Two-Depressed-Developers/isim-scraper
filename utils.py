from typing import Optional, Dict
import random
import asyncio
import httpx
from rapidfuzz import fuzz

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
]

def get_random_header() -> Dict[str, str]:
    """Returns a random User-Agent header to avoid detection"""
    return {'User-Agent': random.choice(USER_AGENTS)}

async def fetch_with_retry(
    client: httpx.AsyncClient, 
    url: str, 
    params: Optional[dict] = None, 
    headers: Optional[dict] = None,
    retries: int = 3
) -> httpx.Response:
    """
    Fetches URL with random delay (jitter), retry logic, and exponential backoff.
    """
    base_headers = get_random_header()
    if headers:
        base_headers.update(headers)
        
    for attempt in range(retries):
        try:
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            response = await client.get(
                url, 
                params=params, 
                headers=base_headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                print(f"Rate limited (429) on {url}. Retrying in {2 ** (attempt + 2)}s...")
                await asyncio.sleep(2 ** (attempt + 2))
            else:
                print(f"Request failed {url}: Status {response.status_code}")
                
        except (httpx.RequestError, httpx.TimeoutException) as e:
            print(f"Network error on {url}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)
            
    return response


def calculate_confidence_score(
    scraped_name: str,
    target_name: str,
    scraped_institution: Optional[str] = None,
    target_institution: Optional[str] = None,
    scraped_text: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> float:
    """
    Calculate confidence score with better field matching and name variations
    """
    
    target_parts = target_name.lower().split()
    scraped_lower = scraped_name.lower()
    
    last_name = target_parts[-1] if target_parts else ""
    first_name = target_parts[0] if len(target_parts) > 0 else ""
    
    name_score = fuzz.ratio(scraped_lower, target_name.lower()) / 100.0
    
    if '.' in scraped_lower:
        if last_name and last_name in scraped_lower:
            first_initial = first_name[0] if first_name else ""
            if first_initial and first_initial in scraped_lower:
                name_score = 0.6
            else:
                name_score = 0.4
        else:
            name_score = 0.2

    if first_name in scraped_lower and last_name in scraped_lower:
        full_match_score = fuzz.ratio(scraped_lower, target_name.lower()) / 100.0
        name_score = max(name_score, full_match_score)
    
    name_contribution = name_score * 0.4
    
    
    institution_contribution = 0.0
    if scraped_institution and target_institution:
        institution_score = fuzz.partial_ratio(
            scraped_institution.lower(),
            target_institution.lower()
        ) / 100.0
        institution_contribution = institution_score * 0.2
    
    
    field_contribution = 0.0
    field_penalty = 0.0
    
    if scraped_text and field_of_study:
        text_lower = scraped_text.lower()
        field_lower = field_of_study.lower()
        
        cs_keywords = [
            'computer', 'software', 'algorithm', 'programming', 'code',
            'computation', 'computational', 'simulation', 'modeling', 'model',
            'machine learning', 'artificial intelligence', 'ai', 'neural',
            'database', 'network', 'internet', 'web', 'digital',
            'embedded', 'microcontroller', 'iot', 'automation',
            'graphics', 'rendering', '3d', 'visualization', 'image processing',
            'docker', 'container', 'cloud', 'distributed', 'parallel',
            'data structure', 'optimization', 'heuristic', 'cellular automata',
            'finite element', 'numerical', 'mesh', 'solver'
        ]
        
        wrong_field_keywords = {
            'civil_engineering': ['gabion', 'tunel', 'most', 'wykop', 'zabudowa', 'bridge', 'tunnel', 
                                  'construction', 'concrete', 'steel structure', 'foundation'],
            'medicine': ['patient', 'clinical', 'disease', 'therapy', 'diagnosis', 
                        'hospital', 'medical', 'health', 'drug', 'pharmaceutical'],
            'pure_biology': ['gene', 'protein', 'dna', 'molecular biology', 'cell culture',
                            'organism', 'species', 'evolution', 'ecological'],
            'chemistry': ['synthesis', 'molecule', 'chemical reaction', 'compound',
                         'titration', 'spectroscopy', 'organic chemistry']
        }
        
        for wrong_field, keywords in wrong_field_keywords.items():
            wrong_matches = sum(1 for kw in keywords if kw in text_lower)
            if wrong_matches >= 2:
                field_penalty = 0.6
                break
            elif wrong_matches == 1:
                field_penalty = max(field_penalty, 0.3)
        
        if 'computer' in field_lower or 'software' in field_lower or 'modeling' in field_lower:
            cs_matches = sum(1 for kw in cs_keywords if kw in text_lower)
            
            if cs_matches >= 3:
                field_contribution = 0.4
            elif cs_matches >= 2:
                field_contribution = 0.3
            elif cs_matches >= 1:
                field_contribution = 0.2
            else:
                if field_penalty == 0:
                    field_penalty = 0.2
    
    
    total_score = name_contribution + institution_contribution + field_contribution - field_penalty
    
    total_score = max(0.0, min(total_score, 1.0))
    
    return round(total_score, 2)