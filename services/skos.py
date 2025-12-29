import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEPARTMENT_URL = "https://skos.agh.edu.pl/jednostka/akademia-gorniczo-hutnicza-im-stanislawa-staszica-w-krakowie/wydzial-inzynierii-metali-i-informatyki-przemyslowej/katedra-informatyki-stosowanej-i-modelowania-366.html"

async def fetch_department_page() -> Optional[str]:
    """Fetches the department listing page HTML."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(DEPARTMENT_URL)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to fetch department page: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Exception fetching department page: {e}")
        return None

def find_member_link(html: str, first_name: str, last_name: str) -> Optional[str]:
    """
    Parses the department page HTML to find the link to a specific member's profile.
    Matches primarily on Last Name, then checks First Name correctness if possible.
    The list format is "Lastname Firstname, degrees...".
    """
    if not html:
        return None

    soup = BeautifulSoup(html, 'lxml')
    
    target_last = last_name.lower()
    target_first = first_name.lower()
    
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        text = link.get_text().strip()
        
        if '/osoba/' not in href:
            continue
            
        text_lower = text.lower()
        
        if target_last in text_lower and target_first in text_lower:
            return urllib.parse.urljoin("https://skos.agh.edu.pl", href)
            
    return None

async def scrape_member_profile(url: str) -> Dict[str, Optional[str]]:
    """
    Scrapes a member's profile page for details.
    Uses the embedded __NEXT_DATA__ JSON for reliability.
    Returns a dict with: title, room, phone, email, url.
    """
    data = {
        "title": None,
        "room": None,
        "phone": None,
        "email": None,
        "url": url
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch profile page: {response.status_code}")
                return data
            html = response.text
            
        soup = BeautifulSoup(html, 'lxml')
        next_data_tag = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_tag:
            import json
            try:
                next_data = json.loads(next_data_tag.string)
                page_props = next_data.get('props', {}).get('pageProps', {})
                user_data = page_props.get('data', {})
                
                workplaces = user_data.get('workplaces', [])
                if workplaces:
                    wp = workplaces[0]
                    
                    office = wp.get('office', {})
                    if office:
                        parts = []
                        if office.get('building'): 
                            bldg = office['building'].split(',')[0].strip()
                            parts.append(bldg)
                        
                        if office.get('room'):
                            room_val = office['room']
                            room_val = room_val.lower().replace("pok.", "").replace("pok", "").strip()
                            parts.append(room_val)
                            
                        data['room'] = " ".join(parts)

                    phones = wp.get('phoneDetails', [])
                    if phones:
                        ph = phones[0]
                        cc = ph.get('countryCode', '')
                        num = ph.get('phoneNumber', '')
                        if cc and num:
                            data['phone'] = f"+{cc} {num}"
                        elif num:
                            data['phone'] = num

                emails = user_data.get('emails', [])
                if emails:
                    reversed_email_html = emails[0]
                    email_html = reversed_email_html[::-1]
                    email_soup = BeautifulSoup(email_html, 'lxml')
                    if email_soup.find('a'):
                        raw_email = email_soup.find('a').get_text().strip()
                        data['email'] = raw_email.replace('#', '@')
                
            except Exception as e:
                logger.error(f"Error parsing __NEXT_DATA__: {e}")
                
        else:
             logger.warning("__NEXT_DATA__ tag not found, fallback to HTML parsing skipped.")
        
    except Exception as e:
        logger.error(f"Exception scraping profile: {e}")
        
    return data

async def scrape_skos_data(first_name: str, last_name: str) -> list[dict]:
    """
    Scraper interface for aggregation service.
    Returns a list containing a single ScrapedData-compatible dict if found.
    """
    try:
        html = await fetch_department_page()
        if not html:
            return []
            
        profile_url = find_member_link(html, first_name, last_name)
        if not profile_url:
            return []
            
        profile_data = await scrape_member_profile(profile_url)
        
        if not profile_data.get('url'):
            return []
            
        return [{
            "source": "skos",
            "url": profile_data['url'],
            "title": f"Profil SKOS: {first_name} {last_name}",
            "description": f"Stanowisko/Tytuł: {profile_data.get('title')}, Pokój: {profile_data.get('room')}",
            "institution": "AGH",
            "raw_data": profile_data
        }]
    except Exception as e:
        logger.error(f"Error in scrape_skos_data: {e}")
        return []
