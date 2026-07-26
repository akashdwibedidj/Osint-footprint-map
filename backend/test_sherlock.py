import asyncio
import sys
from app.services.sherlock_service import sherlock_service

async def main(username: str):
    result = await sherlock_service.search_username(username)
    print(result)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_sherlock.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    asyncio.run(main(username))