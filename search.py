import httpx

async def fetch_all_products():
    all_products = []
    page = 1
    limit = 20

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                "https://api.kittchens.com/api/products",
                params={"page": page, "limit": limit}
            )
            response.raise_for_status()
            data = response.json()

            all_products.extend(data.get("data", []))

            pagination = data.get("pagination", {})
            if not pagination.get("hasNextPage"):
                break

            page += 1

    return all_products



import asyncio

if __name__ == "__main__":
    products = asyncio.run(fetch_all_products())
    print(f"Fetched {len(products)} products")
