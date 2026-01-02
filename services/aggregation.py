import asyncio
from datetime import datetime
from rapidfuzz import fuzz
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


def deduplicate_papers(papers: list) -> list:
    """
    Deduplicate papers based on DOI (exact match) or title similarity.
    Keeps the paper with highest confidence score.
    """
    seen_dois = {}
    seen_titles = {}
    deduplicated = []
    
    for paper in papers:
        doi = paper.get('raw_data', {}).get('doi')
        title = paper.get('title', '').lower().strip()
        
        if doi and doi in seen_dois:
            existing = seen_dois[doi]
            if paper.get('confidenceScore', 0) > existing.get('confidenceScore', 0):
                deduplicated.remove(existing)
                seen_dois[doi] = paper
                deduplicated.append(paper)
        elif doi:
            seen_dois[doi] = paper
            deduplicated.append(paper)
        else:
            is_duplicate = False
            for seen_title, seen_paper in list(seen_titles.items()):
                similarity = fuzz.ratio(title, seen_title) / 100.0
                if similarity >= 0.90:
                    is_duplicate = True
                    if paper.get('confidenceScore', 0) > seen_paper.get('confidenceScore', 0):
                        deduplicated.remove(seen_paper)
                        del seen_titles[seen_title]
                        seen_titles[title] = paper
                        deduplicated.append(paper)
                    break
            
            if not is_duplicate:
                seen_titles[title] = paper
                deduplicated.append(paper)
    
    return deduplicated


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
        data for data in all_scraped_data 
        if data.get('confidenceScore', 0) >= 0.15
    ]
    
    print(f"Total items after filtering (>= 0.15): {len(filtered_data)}")
    
    deduplicated_data = deduplicate_papers(filtered_data)
    
    print(f"Total items after deduplication: {len(deduplicated_data)}")
    
    scraped_data_list = [ScrapedData(**data) for data in deduplicated_data]
    scraped_data_list.sort(key=lambda x: x.confidenceScore, reverse=True)
    
    proposal = DataProposal(
        member=teacher.member_document_id or teacher.teacher_id,
        scrapedData=scraped_data_list,
        createdAt=datetime.now()
    )
    
    return proposal
