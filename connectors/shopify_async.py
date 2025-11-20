import aiohttp
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from data_models import Product

class AsyncShopifyAPI:
    """
    Asynchronous Shopify Admin API Client using aiohttp.
    Designed for high-performance bulk operations.
    """
    def __init__(self, store_url: str, access_token: str, api_version: str = '2024-10'):
        if not store_url: raise ValueError("Shopify Store URL cannot be empty.")
        if not access_token: raise ValueError("Shopify Access Token cannot be empty.")
        
        self.store_url = store_url if store_url.startswith('http') else f"https://{store_url.strip()}"
        self.access_token = access_token
        self.api_version = api_version
        self.graphql_url = f"{self.store_url}/admin/api/{self.api_version}/graphql.json"
        self.headers = {
            'X-Shopify-Access-Token': access_token,
            'Content-Type': 'application/json',
            'User-Agent': 'Sentos-Sync-Python/Async-v1.0'
        }
        
        # Rate Limiting (Token Bucket)
        self.bucket_capacity = 50.0
        self.tokens = 50.0
        self.refill_rate = 2.0 # tokens per second (approx 1000 cost points / 50 cost per query = 20 qps, being conservative)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def _wait_for_token(self, cost: int = 1):
        """Asynchronously waits for rate limit tokens."""
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.bucket_capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens < cost:
                wait_time = (cost - self.tokens) / self.refill_rate
                logging.debug(f"Rate limit hit, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= cost

    async def execute_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a GraphQL query asynchronously."""
        await self._wait_for_token()
        
        payload = {'query': query, 'variables': variables or {}}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.graphql_url, headers=self.headers, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if "errors" in data:
                        # Simple error handling for now
                        raise Exception(f"GraphQL Error: {data['errors']}")
                        
                    return data.get("data", {})
            except Exception as e:
                logging.error(f"Async GraphQL Request Failed: {e}")
                raise e

    async def get_products_async(self, first: int = 10) -> List[Product]:
        """Fetches a list of products asynchronously and returns Pydantic models."""
        query = """
        query getProducts($first: Int!) {
          products(first: $first) {
            edges {
              node {
                id
                title
                handle
                description
                variants(first: 10) {
                  edges {
                    node {
                      id
                      sku
                      title
                      price
                    }
                  }
                }
              }
            }
          }
        }
        """
        data = await self.execute_graphql(query, {"first": first})
        products_data = data.get("products", {}).get("edges", [])
        
        products = []
        for edge in products_data:
            node = edge['node']
            # Map GraphQL response to Pydantic model structure
            # Note: This is a simplified mapping for demonstration
            variants = []
            for v_edge in node.get('variants', {}).get('edges', []):
                v_node = v_edge['node']
                variants.append({
                    "id": v_node['id'],
                    "sku": v_node.get('sku'),
                    "title": v_node.get('title'),
                    "price": v_node.get('price')
                })
            
            product_dict = {
                "id": node['id'],
                "title": node['title'],
                "handle": node.get('handle'),
                "description": node.get('description'),
                "variants": variants
            }
            products.append(Product(**product_dict))
            
        return products
