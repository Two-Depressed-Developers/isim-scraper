from fastapi import FastAPI, BackgroundTasks, HTTPException
import httpx
from config import STRAPI_URL, STRAPI_API_TOKEN
from models import TeacherRequest
from services import aggregate_teacher_data, send_to_strapi, get_existing_urls

app = FastAPI(title="Teacher Data Aggregation Service")


async def process_teacher_scraping(teacher: TeacherRequest):
    try:
        proposal = await aggregate_teacher_data(teacher)
        
        # Deduplication logic
        if isinstance(proposal.member, str):
            existing_urls = await get_existing_urls(proposal.member)
            print(f"Found {len(existing_urls)} existing URLs for member {proposal.member}")
            
            original_count = len(proposal.scrapedData)
            proposal.scrapedData = [
                item for item in proposal.scrapedData 
                if item.url not in existing_urls
            ]
            print(f"Filtered out {original_count - len(proposal.scrapedData)} duplicate items")
        
        if not proposal.scrapedData:
            print("No new data to send to Strapi after deduplication")
            return

        proposal_dict = {
            'member': proposal.member,
            'scrapedData': [data.model_dump() for data in proposal.scrapedData]
        }
        
        result = await send_to_strapi(proposal_dict)
        
        if result:
            print(f"Successfully sent proposal to Strapi: {result.get('data', {}).get('id')}")
        else:
            print("Failed to send proposal to Strapi")
        
    except Exception as e:
        print(f"Error processing teacher scraping: {e}")


@app.get("/")
async def root():
    return {
        "message": "Teacher Data Aggregation Service",
        "version": "1.0.0",
        "strapi_url": STRAPI_URL,
        "strapi_connected": bool(STRAPI_API_TOKEN)
    }


@app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{STRAPI_URL}/health")
            
            return {
                "status": "healthy",
                "strapi_reachable": response.status_code == 200
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.post("/api/scrape/teacher")
async def scrape_teacher(teacher: TeacherRequest, background_tasks: BackgroundTasks):
    if not STRAPI_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="STRAPI_API_TOKEN not configured"
        )
    
    background_tasks.add_task(process_teacher_scraping, teacher)
    
    return {
        "message": "Scraping job started",
        "teacher": f"{teacher.first_name} {teacher.last_name}",
        "status": "processing",
        "note": "Results will be sent to Strapi when complete"
    }


@app.post("/api/scrape/teacher/sync")
async def scrape_teacher_sync(teacher: TeacherRequest):
    if not STRAPI_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="STRAPI_API_TOKEN not configured"
        )
    
    try:
        proposal = await aggregate_teacher_data(teacher)
        
        if isinstance(proposal.member, str):
            existing_urls = await get_existing_urls(proposal.member)
            
            original_count = len(proposal.scrapedData)
            proposal.scrapedData = [
                item for item in proposal.scrapedData 
                if item.url not in existing_urls
            ]
        
        if not proposal.scrapedData:
            return {
                "message": "No new data found (all duplicates)",
                "strapi_response": None,
                "scraped_items": 0
            }

        proposal_dict = {
            'member': proposal.member,
            'scrapedData': [data.model_dump() for data in proposal.scrapedData]
        }
        
        result = await send_to_strapi(proposal_dict)
        
        if result:
            return {
                "message": "Scraping completed and sent to Strapi",
                "strapi_response": result,
                "scraped_items": len(proposal.scrapedData)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send data to Strapi"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during scraping: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)