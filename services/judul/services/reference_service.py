"""Fetch referensi paper dari Semantic Scholar API."""

import requests
from typing import List, Dict, Optional
import time
from config.settings import settings


class ReferenceService:
    """Service untuk mengambil referensi paper dari Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        # Inisialisasi service
        self.session = requests.Session()
        # Default timeout untuk request
        self.timeout = 10

    def search_papers(
        self,
        keywords: List[str],
        limit: int = 3,
        min_citations: int = 5
    ) -> List[Dict]:

        print(f"\n{'='*60}")
        print(f"🔍 SEARCHING PAPERS")
        print(f"{'='*60}")
        print(f"Keywords: {keywords}")
        print(f"Limit: {limit}, Min Citations: {min_citations}")

        try:
            # Join keywords
            query = " ".join(keywords)
            print(f"Query string: '{query}'")

            # Call API
            raw_papers = self._call_semantic_scholar_api(query, limit * 2)
            print(f"✅ API returned: {len(raw_papers)} papers")

            if not raw_papers:
                print(f"⚠️ No papers from API - using fallback")
                return self._get_fallback_references(keywords)

            # Filter
            filtered_papers = [
                paper for paper in raw_papers
                if paper.get('citationCount', 0) >= min_citations
            ]
            print(
                f"📊 After citation filter (>={min_citations}): {len(filtered_papers)} papers")

            # If empty after filter, lower the threshold
            if not filtered_papers and raw_papers:
                print(f"⚠️ No papers passed citation filter. Lowering threshold to 0...")
                filtered_papers = raw_papers

            # Sort
            sorted_papers = sorted(
                filtered_papers,
                key=lambda x: x.get('citationCount', 0),
                reverse=True
            )
            print(f"🔄 After sort: {len(sorted_papers)} papers")

            # Take top
            top_papers = sorted_papers[:limit]
            print(f"✂️ After slice (top {limit}): {len(top_papers)} papers")

            if not top_papers:
                print(f"⚠️ No papers after processing - using fallback")
                return self._get_fallback_references(keywords)

            # Format
            formatted_papers = []
            for i, paper in enumerate(top_papers):
                try:
                    formatted = self._format_paper(paper)
                    if formatted:
                        formatted_papers.append(formatted)
                        print(f"✅ Paper {i+1} formatted successfully")
                    else:
                        print(
                            f"⚠️ Paper {i+1} returned None from _format_paper")
                except Exception as e:
                    print(f"❌ Error formatting paper {i+1}: {e}")

            print(f"📝 Final result: {len(formatted_papers)} formatted papers")

            if not formatted_papers:
                print(f"⚠️ No formatted papers - using fallback")
                return self._get_fallback_references(keywords)

            print(f"{'='*60}\n")
            return formatted_papers

        except Exception as e:
            print(f"❌ Exception in search_papers: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_references(keywords)

    def _call_semantic_scholar_api(
        self,
        query: str,
        limit: int
    ) -> List[Dict]:
        """
        Internal method untuk call Semantic Scholar API.
        """
        url = f"{self.BASE_URL}/paper/search"

        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,abstract,citationCount,url,externalIds,venue"
        }

        # Headers dengan API Key
        headers = {}
        if settings.SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY
            print("Using Semantic Scholar API Key from settings.")
        else:
            print("No API KEY, using anonymous access to Semantic Scholar API.")

        try:
            # Sleep sebelum request
            if settings.SEMANTIC_SCHOLAR_API_KEY:
                time.sleep(1)  # Tunggu 1 detik sebelum request with API Key
            else:
                time.sleep(3)  # Tunggu 3 detik sebelum request without API Key

            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            # Check status
            if response.status_code == 429:
                print("Rate Limited!")
                time.sleep(5)  # Delay sebelum retry
                return []

            response.raise_for_status()

            data = response.json()
            return data.get('data', [])

        except requests.exceptions.Timeout:
            print("Semantic Scholar API timeout")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Semantic Scholar API error: {e}")
            return []

    def _format_paper(self, paper: Dict) -> Dict:
        """Format paper dari Semantic Scholar ke format sistem kita."""

    # Extract authors
        authors = paper.get('authors', [])

        if not authors:
            author_str = "Unknown Authors"
        elif len(authors) == 1:
            author_str = authors[0].get('name', 'Unknown')
        elif len(authors) == 2:
            author_str = f"{authors[0].get('name', 'Unknown')} & {authors[1].get('name', 'Unknown')}"
        else:
            author_str = f"{authors[0].get('name', 'Unknown')}, et al."

        # Extract other fields
        year = paper.get('year', 'n.d.')
        title = paper.get('title', 'Untitled')
        venue = paper.get('venue', 'Unknown Venue')

        # Extract DOI or URL
        external_ids = paper.get('externalIds', {})
        doi = external_ids.get('DOI')

        if doi:
            link = f"https://doi.org/{doi}"
        else:
            link = paper.get('url', 'https://www.semanticscholar.org')

        # Get citation count
        citation_count = paper.get('citationCount', 0)

        # Format sitasi
        sitasi = f"{author_str} ({year}). {title}. {venue}."

        if citation_count > 0:
            sitasi += f" (Cited by {citation_count})"

        return {
            "sitasi": sitasi,
            "link": link
        }

    def _get_fallback_references(self, keywords: List[str]) -> List[Dict]:

        keyword_str = ", ".join(keywords)

        return [
            {
                "sitasi": f"Silakan cari paper terkait '{keyword_str}' secara manual di Google Scholar.",
                "link": f"https://scholar.google.com/scholar?q={'+'.join(keywords)}"
            },
            {
                "sitasi": "Atau gunakan Semantic Scholar untuk pencarian lebih spesifik.",
                "link": f"https://www.semanticscholar.org/search?q={'+'.join(keywords)}"
            }
        ]

    def validate_paper_relevance(
        self,
        paper_title: str,
        keywords: List[str]
    ) -> bool:
        """ Validasi relevansi paper dengan keywords """
        title_lower = paper_title.lower()

        # Check keyword yang muncul di title
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return True

        return False


reference_service = ReferenceService()
