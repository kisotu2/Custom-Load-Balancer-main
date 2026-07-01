import asyncio
import aiohttp
from collections import defaultdict
import matplotlib.pyplot as plt

NUM_REQUESTS = 10000
MAX_CONCURRENCY = 100  # at most 100 simultaneous HTTP requests
LB_URL = "http://localhost:6000/home?id="

async def fetch(sem, session, url):
    # throttle with semaphore
    async with sem:
        try:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
                server_msg = data.get("container_response", {}).get("message", "")
                # Extract "Server lbX" → "lbX"
                return server_msg.split("Server")[-1].strip()
        except:
            return "error"

async def main():
    counts = defaultdict(int)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        print("⏳ Waiting 10 seconds for servers to be ready…")
        await asyncio.sleep(10)

        tasks = [
            asyncio.create_task(fetch(sem, session, LB_URL + str(i)))
            for i in range(NUM_REQUESTS)
        ]

        for coro in asyncio.as_completed(tasks):
            server_id = await coro
            counts[server_id] += 1

    # Output counts
    print("\nRequest Distribution (10 000 requests):")
    for server, count in counts.items():
        print(f"{server}: {count} requests")

    # Plot bar chart
    plt.bar(counts.keys(), counts.values(), color='steelblue')
    plt.title("Load Distribution Across Servers")
    plt.xlabel("Server ID")
    plt.ylabel("Requests Handled")
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig("client/load_distribution.png")
    print("\nBar chart saved as client/load_distribution.png")

if __name__ == "__main__":
    asyncio.run(main())
