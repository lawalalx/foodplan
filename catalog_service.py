
import httpx
import asyncio
from typing import Dict, List
from loguru import logger

class CatalogService:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.categories: List[Dict] = []
        self.category_map: Dict[str, Dict] = {}

    async def load_categories(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/categories")
            resp.raise_for_status()
            data = resp.json().get("data", [])

        self.categories = data
        self.category_map = {
            cat["name"].strip().lower(): cat for cat in data
        }

    def get_category_context_string(self) -> str:
        """
        Build dynamic category + units string for LLM prompt.
        """
        lines = []
        for cat in self.categories:
            name = cat["name"]
            units = ", ".join(cat.get("allowed_units", []))
            lines.append(f"- {name}: allowed units → {units}")
        result =  "\n".join(lines)
        return result
    
    
    def get_unique_categories(self, normalize: bool = True) -> List[str]:
        """
        Returns a list of unique category names.
        :param normalize: If True, converts names to lowercase and strips whitespace.
        """
        if normalize:
            unique = list({cat["name"].strip().lower() for cat in self.categories})
        else:
            unique = list({cat["name"] for cat in self.categories})
        return unique
