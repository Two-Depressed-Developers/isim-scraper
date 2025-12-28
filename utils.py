from typing import Optional
from rapidfuzz import fuzz


def calculate_confidence_score(
    scraped_name: str,
    target_name: str,
    scraped_institution: Optional[str] = None,
    target_institution: Optional[str] = None,
    scraped_text: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> float:
    """
    Calculate confidence score with better field matching and name variations
    """
    
    # 1. NAME MATCHING (40% weight)
    # Handle various name formats: "Ł. Madej", "Lukasz Madej", "L. Madej"
    target_parts = target_name.lower().split()
    scraped_lower = scraped_name.lower()
    
    # Check if last name is in scraped name
    last_name = target_parts[-1] if target_parts else ""
    first_name = target_parts[0] if len(target_parts) > 0 else ""
    
    # Base name score
    name_score = fuzz.ratio(scraped_lower, target_name.lower()) / 100.0
    
    # Better handling of initials vs full names
    # "Ł. Madej" vs "łukasz madej" should score lower than "Lukasz Madej"
    if '.' in scraped_lower:  # Has initials
        # Only counts if last name matches well
        if last_name and last_name in scraped_lower:
            # Check if first initial matches
            first_initial = first_name[0] if first_name else ""
            if first_initial and first_initial in scraped_lower:
                name_score = 0.6  # Decent but not perfect match
            else:
                name_score = 0.4  # Last name only
        else:
            name_score = 0.2
    
    # Full name match is better
    if first_name in scraped_lower and last_name in scraped_lower:
        # Check how close the full match is
        full_match_score = fuzz.ratio(scraped_lower, target_name.lower()) / 100.0
        name_score = max(name_score, full_match_score)
    
    name_contribution = name_score * 0.4  # 40% of total
    
    
    # 2. INSTITUTION MATCHING (20% weight)
    institution_contribution = 0.0
    if scraped_institution and target_institution:
        institution_score = fuzz.partial_ratio(
            scraped_institution.lower(),
            target_institution.lower()
        ) / 100.0
        institution_contribution = institution_score * 0.2
    
    
    # 3. FIELD MATCHING (40% weight) - This is critical!
    field_contribution = 0.0
    field_penalty = 0.0
    
    if scraped_text and field_of_study:
        text_lower = scraped_text.lower()
        field_lower = field_of_study.lower()
        
        # Define field-specific keywords
        cs_keywords = [
            'computer', 'software', 'algorithm', 'programming', 'code',
            'computation', 'computational', 'simulation', 'modeling', 'model',
            'machine learning', 'artificial intelligence', 'ai', 'neural',
            'database', 'network', 'internet', 'web', 'digital',
            'embedded', 'microcontroller', 'iot', 'automation',
            'graphics', 'rendering', '3d', 'visualization', 'image processing',
            'docker', 'container', 'cloud', 'distributed', 'parallel',
            'data structure', 'optimization', 'heuristic', 'cellular automata',
            'finite element', 'numerical', 'mesh', 'solver'
        ]
        
        # Wrong field indicators (strong negative signals)
        wrong_field_keywords = {
            'civil_engineering': ['gabion', 'tunel', 'most', 'wykop', 'zabudowa', 'bridge', 'tunnel', 
                                  'construction', 'concrete', 'steel structure', 'foundation'],
            'medicine': ['patient', 'clinical', 'disease', 'therapy', 'diagnosis', 
                        'hospital', 'medical', 'health', 'drug', 'pharmaceutical'],
            'pure_biology': ['gene', 'protein', 'dna', 'molecular biology', 'cell culture',
                            'organism', 'species', 'evolution', 'ecological'],
            'chemistry': ['synthesis', 'molecule', 'chemical reaction', 'compound',
                         'titration', 'spectroscopy', 'organic chemistry']
        }
        
        # Check for wrong field (major penalty)
        for wrong_field, keywords in wrong_field_keywords.items():
            wrong_matches = sum(1 for kw in keywords if kw in text_lower)
            if wrong_matches >= 2:
                field_penalty = 0.6  # Heavy penalty
                break
            elif wrong_matches == 1:
                field_penalty = max(field_penalty, 0.3)  # Moderate penalty
        
        # Check for CS keywords (bonus)
        if 'computer' in field_lower or 'software' in field_lower or 'modeling' in field_lower:
            cs_matches = sum(1 for kw in cs_keywords if kw in text_lower)
            
            if cs_matches >= 3:
                field_contribution = 0.4  # Strong match
            elif cs_matches >= 2:
                field_contribution = 0.3  # Good match
            elif cs_matches >= 1:
                field_contribution = 0.2  # Weak match
            else:
                # No CS keywords found
                if field_penalty == 0:
                    field_penalty = 0.2  # Mild penalty if no wrong field but also no CS
    
    
    # 4. COMBINE SCORES
    total_score = name_contribution + institution_contribution + field_contribution - field_penalty
    
    # Ensure score is between 0 and 1
    total_score = max(0.0, min(total_score, 1.0))
    
    return round(total_score, 2)