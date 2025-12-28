from .google_scholar import scrape_google_scholar
from .orcid import scrape_orcid_info
from .researchgate import scrape_researchgate
from .university import scrape_university_websites
from .dblp import scrape_dblp
from .arxiv import scrape_arxiv
from .semantic_scholar import scrape_semantic_scholar

__all__ = [
    'scrape_google_scholar',
    'scrape_orcid_info',
    'scrape_researchgate',
    'scrape_university_websites',
    'scrape_dblp',
    'scrape_arxiv',
    'scrape_semantic_scholar'
]
