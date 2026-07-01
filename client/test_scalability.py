import asyncio
import aiohttp
import matplotlib.pyplot as plt
from collections import defaultdict
import subprocess
import time

LB_HOME_URL = "http://localhost:6000/home?id="
LB_ADD_URL = "http://localhost:6000/add"
LB_RM_URL = "http://localhost:6000/rm"
NUM_REQUESTS = 10000
MAX_CONCURRENCY = 100  # limit concurrent HTTP requests
STARTUP_DELAY = 10     # seconds to wait after /add

async def fetch(sem, session, url):
    async with sem:
        try:
            async with session.get(url, timeout=10) as response:
                data = await response.json()
                msg = data.get("container_response", {}).get("message", "")
                return msg.split("Server")[-1].strip()
        except:
            return "error"

async def send_requests():
    counts = defaultdict(int)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(fetch(sem, session, LB_HOME_URL + str(i)))
            for i in range(NUM_REQUESTS)
        ]
        for coro in asyncio.as_completed(tasks):
            sid = await coro
            counts[sid] += 1

    return counts

def add_servers(n):
    hostnames = [f"auto{i}" for i in range(n)]
    payload = {
        "n": n,
        "hostnames": hostnames
    }
    subprocess.run([
        "curl", "-s", "-X", "POST", LB_ADD_URL,
        "-H", "Content-Type: application/json",
        "-d", str(payload).replace("'", '"')
    ])

def remove_all_servers():
    subprocess.run([
        "curl", "-s", "-X", "DELETE", LB_RM_URL,
        "-H", "Content-Type: application/json",
        "-d", '{"n": 6}'
    ])

async def main():
    results = []

    for n in range(2, 7):  # N = 2 to 6
        print(f"\n▶️ Testing with {n} servers...")
        remove_all_servers()
        time.sleep(2)  # allow removal to propagate
        add_servers(n)
        print(f"⏳ Waiting {STARTUP_DELAY}s for {n} servers to boot…")
        await asyncio.sleep(STARTUP_DELAY)

        counts = await send_requests()
        total_handled = sum(v for k, v in counts.items() if k != "error")
        avg = total_handled / n if n else 0
        results.append((n, avg))

        errors = counts.get("error", 0)
        print(f"Handled: {total_handled}  Errors: {errors}")
        print(f"Average load per server for N={n}: {avg:.2f}")

    # Plot scalability line chart
    x = [r[0] for r in results]
    y = [r[1] for r in results]

    plt.plot(x, y, marker='o')
    plt.title("Average Requests per Server vs Number of Servers")
    plt.xlabel("Number of Servers (N)")
    plt.ylabel("Average Requests per Server")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("client/scalability_chart.png")
    print("\n📊 Line chart saved as client/scalability_chart.png")

if __name__ == "__main__":
    asyncio.run(main())
