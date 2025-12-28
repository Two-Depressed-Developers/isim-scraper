import asyncio
from datetime import datetime
from models import TeacherRequest, DataProposal, ScrapedData
from scrapers import (
    scrape_google_scholar,
    scrape_university_websites,
    scrape_researchgate,
    scrape_orcid_info,
    scrape_dblp,
    scrape_arxiv,
    scrape_semantic_scholar
)


async def aggregate_teacher_data(teacher: TeacherRequest) -> DataProposal:
    print(f"Starting aggregation for {teacher.first_name} {teacher.last_name}")
    
    tasks = [
        scrape_google_scholar(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution,
            teacher.field_of_study
        ),
        scrape_university_websites(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution
        ),
        scrape_researchgate(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution,
            teacher.field_of_study
        ),
        scrape_orcid_info(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution,
            teacher.field_of_study
        ),
        scrape_dblp(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution,
            teacher.field_of_study
        ),
        scrape_arxiv(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution,
            teacher.field_of_study
        ),
        scrape_semantic_scholar(
            teacher.first_name,
            teacher.last_name,
            teacher.current_institution,
            teacher.field_of_study
        )
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_scraped_data = []
    for result in results:
        if isinstance(result, list):
            all_scraped_data.extend(result)
    
    print(f"Total scraped items before filtering: {len(all_scraped_data)}")
    for item in all_scraped_data:
        print(f"  - {item.get('source')}: confidence={item.get('confidenceScore', 0)}")
    
    filtered_data = [
        ScrapedData(**data) for data in all_scraped_data 
        if data.get('confidenceScore', 0) >= 0.15
    ]
    
    print(f"Total items after filtering (>= 0.15): {len(filtered_data)}")
    
    filtered_data.sort(key=lambda x: x.confidenceScore, reverse=True)
    
    proposal = DataProposal(
        member=teacher.member_document_id or teacher.teacher_id,
        scrapedData=filtered_data,
        createdAt=datetime.now()
    )
    
    return proposal
