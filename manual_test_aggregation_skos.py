import asyncio
import logging
from services.aggregation import aggregate_teacher_data
from models import TeacherRequest

logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing Aggregation with SKOS integration...")
    
    teacher = TeacherRequest(
        first_name="Piotr",
        last_name="Hajder",
        current_institution="AGH",
        field_of_study="Computer Science"
    )
    
    proposal = await aggregate_teacher_data(teacher)
    
    print("\n--- Aggregation Result ---")
    print(f"Member ID: {proposal.member}")
    print(f"Total Scraped Items: {len(proposal.scrapedData)}")
    
    found_skos = False
    for item in proposal.scrapedData:
        print(f"Source: {item.source}")
        print(f"Title: {item.title}")
        print(f"Confidence: {item.confidenceScore}")
        if item.source == 'skos':
            found_skos = True
            print("SKOS Raw Data:", item.raw_data)
            
    if found_skos:
        print("\nSUCCESS: SKOS data found in aggregation result.")
    else:
        print("\nFAILURE: SKOS data NOT found in aggregation result.")

if __name__ == "__main__":
    asyncio.run(main())
