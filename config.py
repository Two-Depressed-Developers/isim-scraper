import os
from dotenv import load_dotenv

load_dotenv()

STRAPI_URL = os.getenv('STRAPI_URL', 'http://localhost:1337')
STRAPI_API_TOKEN = os.getenv('STRAPI_API_TOKEN', '')
