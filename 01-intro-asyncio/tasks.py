import asyncio


async def long_running_task(time_to_sleep):
    print(f"Being sleep for {time_to_sleep}")
    await asyncio.sleep(time_to_sleep)
    print(f"Awake sleep for {time_to_sleep}")


# # one
# asyncio.run(long_running_task(1))


# # two
# async def main():
#     await long_running_task(3)


# asyncio.run(main())

# # three
# async def task():
#     task1 = asyncio.create_task(long_running_task(1))
#     await task1


async def tasks():
    task1 = asyncio.create_task(long_running_task(1))
    task2 = asyncio.create_task(long_running_task(2))
    task3 = asyncio.create_task(long_running_task(3))
    await asyncio.gather(task1, task2, task3)


# asyncio.run(task())
asyncio.run(tasks())


# four
# async def main():
#     tasks = []
#     for i in range(1, 4):
#         tasks.append(long_running_task(i))
#     await asyncio.wait(tasks)


# asyncio.run(main())
