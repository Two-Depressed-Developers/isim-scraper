from typing import Optional
import httpx
from config import STRAPI_URL, STRAPI_API_TOKEN


async def send_to_strapi(proposal: dict) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'Authorization': f'Bearer {STRAPI_API_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            strapi_data = {
                "data": {
                    "member": proposal.get('member'),
                    "scrapedData": proposal['scrapedData']
                }
            }
            
            response = await client.post(
                f"{STRAPI_URL}/api/data-proposals",
                json=strapi_data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Error sending to Strapi: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        return None


async def get_existing_urls(member_document_id: str) -> set[str]:
    if not member_document_id or not isinstance(member_document_id, str):
        return set()
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'Authorization': f'Bearer {STRAPI_API_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            # Query to find proposals for this member and get their scraped data
            # Using filters[member][documentId][$eq] as requested
            url = f"{STRAPI_URL}/api/data-proposals"
            params = {
                "filters[member][documentId][$eq]": member_document_id
            }
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json().get('data', [])
                existing_urls = set()
                
                for proposal in data:
                    scraped_items = proposal.get('scrapedData', [])
                    # Strapi might return it as a list of dicts directly or nested depending on structure
                    # Assuming standard dynamic zone or component list structure
                    if scraped_items:
                        for item in scraped_items:
                            if url_val := item.get('url'):
                                existing_urls.add(url_val)
                                
                return existing_urls
            else:
                print(f"Error fetching existing URLs: {response.status_code} - {response.text}")
                return set()
                
    except Exception as e:
        print(f"Exception fetching existing URLs: {e}")
        return set()
