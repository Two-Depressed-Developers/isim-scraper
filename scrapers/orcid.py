from typing import List, Optional
import httpx
from utils import calculate_confidence_score


async def scrape_orcid_info(
    first_name: str,
    last_name: str,
    institution: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> List[dict]:
    results = []
    full_name = f"{first_name} {last_name}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_url = f"https://pub.orcid.org/v3.0/search/?q={full_name.replace(' ', '+')}"
            
            headers = {
                'Accept': 'application/json'
            }
            
            response = await client.get(search_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data:
                    for result in data['result'][:3]:
                        orcid_id = result.get('orcid-identifier', {}).get('path')
                        
                        if orcid_id:
                            result_name = result.get('orcid-identifier', {}).get('name', '')
                            
                            scraped_institution = None
                            employment = result.get('employment-summary', [])
                            if employment and len(employment) > 0:
                                scraped_institution = employment[0].get('organization', {}).get('name', '')
                            
                            confidence = calculate_confidence_score(
                                result_name,
                                full_name,
                                scraped_institution=scraped_institution,
                                target_institution=institution
                            )
                            
                            results.append({
                                'source': 'ORCID',
                                'url': f"https://orcid.org/{orcid_id}",
                                'title': f"ORCID Profile: {orcid_id}",
                                'description': f"ORCID identifier for researcher",
                                'authors': result_name,
                                'confidenceScore': confidence,
                                'raw_data': {
                                    'orcid_id': orcid_id
                                }
                            })
    
    except Exception as e:
        print(f"Error searching ORCID: {e}")
    
    return results
