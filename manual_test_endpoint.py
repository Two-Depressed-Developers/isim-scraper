import asyncio
from main import update_member_profile
from models import TeacherRequest

async def main():
    print("Testing /api/update-member-profile logic...")
    
    teacher = TeacherRequest(
        first_name="Piotr",
        last_name="Hajder",
        member_document_id="dummy_doc_id_123"
    )
    
    response = await update_member_profile(teacher)
    
    print("\nResponse:", response)

if __name__ == "__main__":
    asyncio.run(main())
