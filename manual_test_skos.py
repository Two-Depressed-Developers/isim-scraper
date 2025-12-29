import asyncio
import logging
from services.skos import fetch_department_page, find_member_link, scrape_member_profile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting manual test for SKOS scraper")

    logger.info("Fetching department page...")
    html = await fetch_department_page()
    
    if not html:
        logger.error("Failed to fetch department page.")
        return

    logger.info(f"Successfully fetched page ({len(html)} chars).")

    first_name = "Piotr"
    last_name = "Hajder"
    
    logger.info(f"Looking for member: {first_name} {last_name}")
    profile_url = find_member_link(html, first_name, last_name)
    
    if not profile_url:
        logger.error("Member not found!")
        return
        
    logger.info(f"Found profile URL: {profile_url}")

    logger.info("Scraping profile details...")
    profile_data = await scrape_member_profile(profile_url)
    
    logger.info("Scraped Data:")
    for key, value in profile_data.items():
        logger.info(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())
