import asyncio
import time

async def say_hello():
    await asyncio.sleep(2)
    print("Hello, world!")

async def say_bye():
    await asyncio.sleep(2)
    print("Bye, world!")

async def main():
    start = time.time()

    await asyncio.gather(say_hello(), say_bye())

    total = time.time() - start
    print(f"Time taken: {total} seconds")

asyncio.run(main()) 