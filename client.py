import asyncio
import time

import aiohttp


async def download_pep(pep_number: int) -> bytes:
    url = f"https://www.python.org/dev/peps/pep-{pep_number}/"
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url) as resp:
            content = await resp.read()
            return content


async def write_to_file(pep_number: int, content: bytes) -> None:
    filename = f"async_{pep_number}.html"
    with open(filename, "wb") as f:
        f.write(content)


async def web_scrape_task(pep_number: int) -> None:
    content = await download_pep(pep_number)
    await write_to_file(pep_number, content)


async def main() -> None:
    tasks = []
    for i in range(8010, 8016):
        tasks.append(web_scrape_task(i))
    await asyncio.wait(tasks)


if __name__ == "__main__":
    s = time.perf_counter()
    asyncio.run(main())
    elapsed = time.perf_counter() - s
    print(f"Execution time: {elapsed:0.2f} seconds.")
