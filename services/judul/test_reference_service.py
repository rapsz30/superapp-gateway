# test_reference_service.py - FIXED VERSION with API Key

from services.reference_service import reference_service
from config.settings import settings
import requests
import time

print("="*50)
print("TESTING REFERENCE SERVICE")
print("="*50)

# Check API Key
if settings.SEMANTIC_SCHOLAR_API_KEY:
    print(f"✅ API Key: {settings.SEMANTIC_SCHOLAR_API_KEY[:10]}...\n")
else:
    print("⚠️ No API Key configured!\n")

keywords = ["collaborative filtering", "recommendation system"]
print(f"Searching papers with keywords: {keywords}")

# =================================================================
# DEBUG: Test API Call Directly WITH API KEY
# =================================================================

print("\nDEBUG: Calling API directly (with API key)...")

url = "https://api.semanticscholar.org/graph/v1/paper/search"
params = {
    "query": " ".join(keywords),
    "limit": 3,
    "fields": "title,authors,year,citationCount,url,externalIds"
}

# ADD API KEY TO HEADERS
headers = {}
if settings.SEMANTIC_SCHOLAR_API_KEY:
    headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY
    print("✅ Using API Key in request")

print(f"URL: {url}")
print(f"Params: {params}")
print(f"Headers: {headers}")

time.sleep(1)  # Rate limiting

try:
    response = requests.get(
        url,
        params=params,
        headers=headers,  # ← ADDED!
        timeout=10
    )

    print(f"\nDEBUG: Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"DEBUG: Response keys: {data.keys()}")
        print(f"DEBUG: Total results: {data.get('total', 0)}")
        print(f"DEBUG: Data length: {len(data.get('data', []))}")

        if data.get('data'):
            print(f"\nDEBUG: First paper sample:")
            first_paper = data['data'][0]
            print(f"  Title: {first_paper.get('title')}")
            print(f"  Year: {first_paper.get('year')}")
            print(f"  Citations: {first_paper.get('citationCount')}")
        else:
            print("\nDEBUG: data field is empty!")
    else:
        print(f"DEBUG: Error - {response.text}")

except Exception as e:
    print(f"DEBUG: Exception - {e}")

# =================================================================
# Test via service
# =================================================================

print("\n" + "="*50)
print("Now testing via reference_service...")
print("="*50)

papers = reference_service.search_papers(keywords, limit=3, min_citations=0)

print(f"\nFound {len(papers)} papers:\n")

for i, paper in enumerate(papers):
    print(f"Paper #{i+1}:")
    print(f"  Sitasi: {paper['sitasi']}")
    print(f"  Link: {paper['link']}")
    print()

print("="*50)
