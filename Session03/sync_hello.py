import asyncio
import time

def say_hello():
    time.sleep(2)
    print("Hello, world!")

def say_bye():
    time.sleep(2)
    print("Bye, world!")

start = time.time()
say_hello()
say_bye()
end = time.time()
print(f"Time taken: {end - start} seconds")