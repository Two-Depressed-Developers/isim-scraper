from typing import List, Optional
import httpx
from urllib.parse import quote
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
            search_query = f"given-names:{quote(first_name)} AND family-name:{quote(last_name)}"
            search_url = f"https://pub.orcid.org/v3.0/search/?q={search_query}"
            
            headers = {
                'Accept': 'application/json'
            }
            
            print(f"Searching ORCID for: {full_name}")
            response = await client.get(search_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data:
                    total_profiles = len(data['result'])
                    checking = min(5, total_profiles)
                    print(f"Found {total_profiles} ORCID profiles, checking top {checking}")
                    for result in data['result'][:5]:
                        orcid_id = result.get('orcid-identifier', {}).get('path')
                        
                        if orcid_id:
                            record_url = f"https://pub.orcid.org/v3.0/{orcid_id}"
                            record_response = await client.get(record_url, headers=headers)
                            
                            if record_response.status_code != 200:
                                continue
                            
                            record_data = record_response.json()
                            
                            person_data = record_data.get('person', {})
                            name_data = person_data.get('name', {})
                            given_name = name_data.get('given-names', {}).get('value', '')
                            family_name = name_data.get('family-name', {}).get('value', '')
                            result_name = f"{given_name} {family_name}".strip()
                            
                            if not result_name:
                                continue
                            
                            all_institutions = []
                            activities = record_data.get('activities-summary', {})
                            
                            employments = activities.get('employments', {}).get('affiliation-group', [])
                            for emp_group in employments:
                                summaries = emp_group.get('summaries', [])
                                for summary in summaries:
                                    emp_summary = summary.get('employment-summary', {})
                                    org = emp_summary.get('organization', {})
                                    org_name = org.get('name')
                                    if org_name:
                                        all_institutions.append(org_name)
                            
                            educations = activities.get('educations', {}).get('affiliation-group', [])
                            for edu_group in educations:
                                summaries = edu_group.get('summaries', [])
                                for summary in summaries:
                                    edu_summary = summary.get('education-summary', {})
                                    org = edu_summary.get('organization', {})
                                    org_name = org.get('name')
                                    if org_name:
                                        all_institutions.append(org_name)
                            
                            scraped_institution = all_institutions[0] if all_institutions else None
                            
                            profile_confidence = calculate_confidence_score(
                                result_name,
                                full_name,
                                scraped_institution=scraped_institution,
                                target_institution=institution
                            )
                            
                            institution_match = False
                            institution_mismatch = False
                            
                            if institution and all_institutions:
                                target_lower = institution.lower()
                                
                                agh_keywords = ['agh', 'akademia górniczo', 'akademia gorniczo']
                                
                                for inst in all_institutions:
                                    inst_lower = inst.lower()
                                    
                                    has_agh = any(keyword in inst_lower for keyword in agh_keywords)
                                    has_target = any(keyword in inst_lower for keyword in agh_keywords if keyword in target_lower)
                                    
                                    if has_agh or has_target:
                                        institution_match = True
                                        profile_confidence = min(1.0, profile_confidence + 0.5)
                                        break
                                
                                if not institution_match:
                                    for inst in all_institutions:
                                        inst_lower = inst.lower()
                                        
                                        if any(keyword in inst_lower for keyword in ['university', 'uniwersytet', 'politechnika', 'uczelnia']):
                                            institution_mismatch = True
                                            profile_confidence = max(0.0, profile_confidence - 0.5)
                                            break
                            
                            inst_info = f" at {scraped_institution}" if scraped_institution else ""
                            if len(all_institutions) > 1:
                                inst_info = f" at {scraped_institution} (+{len(all_institutions)-1} more)"
                            match_info = " [INSTITUTION MATCH]" if institution_match else ""
                            if institution_mismatch:
                                match_info = " [DIFFERENT INSTITUTION]"
                            print(f"ORCID profile: {result_name}{inst_info} ({orcid_id}) - confidence: {profile_confidence:.2f}{match_info}")
                            
                            profile_threshold = 0.40
                            if institution_match:
                                profile_threshold = 0.3
                            
                            if profile_confidence >= profile_threshold:
                                print(f"Found ORCID author: {result_name} with {profile_confidence:.2f} confidence")
                                
                                works_url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
                                works_response = await client.get(works_url, headers=headers)
                                
                                if works_response.status_code == 200:
                                    works_data = works_response.json()
                                    group = works_data.get('group', [])
                                    
                                    print(f"Found {len(group)} works from ORCID")
                                    
                                    for work_group in group:
                                        work_summary = work_group.get('work-summary', [])
                                        if work_summary:
                                            work = work_summary[0]
                                            
                                            title_obj = work.get('title', {})
                                            title = title_obj.get('title', {}).get('value', 'Untitled Work')
                                            
                                            pub_date = work.get('publication-date')
                                            year = pub_date.get('year', {}).get('value', 'Unknown') if pub_date else 'Unknown'
                                            
                                            external_ids = work.get('external-ids', {}).get('external-id', [])
                                            doi = None
                                            for ext_id in external_ids:
                                                if ext_id.get('external-id-type') == 'doi':
                                                    doi = ext_id.get('external-id-value')
                                                    break
                                            
                                            work_url = f"https://orcid.org/{orcid_id}"
                                            if doi:
                                                work_url = f"https://doi.org/{doi}"
                                            
                                            if institution_match or profile_confidence >= 0.8:
                                                work_confidence = profile_confidence
                                            else:
                                                work_confidence = calculate_confidence_score(
                                                    result_name,
                                                    full_name,
                                                    scraped_institution=scraped_institution,
                                                    target_institution=institution,
                                                    scraped_text=title,
                                                    field_of_study=field_of_study
                                                )
                                            
                                            results.append({
                                                'source': 'ORCID',
                                                'url': work_url,
                                                'title': title,
                                                'description': f"Published in {year}",
                                                'authors': result_name,
                                                'confidenceScore': work_confidence,
                                                'raw_data': {
                                                    'orcid_id': orcid_id,
                                                    'year': year,
                                                    'doi': doi
                                                }
                                            })
                                else:
                                    print(f"Failed to fetch works for {orcid_id}: {works_response.status_code}")
                else:
                    print("No results found in ORCID response")
            else:
                print(f"ORCID search failed with status: {response.status_code}")
    
    except Exception as e:
        print(f"Error searching ORCID: {e}")
    
    return results
