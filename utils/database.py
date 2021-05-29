import aiosqlite
import asyncio


async def tableexist(table):
    async with aiosqlite.connect('./main.db') as db:
        async with db.execute(f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table}'") as cursor:
            async for data in cursor:
                if data[0] == 1:
                    print(data[0])
                    return True
                else:
                    print(data[0])
                    return False


async def tablecreate(table, fields):
    query = f"CREATE TABLE IF NOT EXISTS {table}"
    data = []

    for key in fields:
        data.append(key, fields[key])

    return data


async def fetchall(table):
    data = []
    async with aiosqlite.connect('./main.db') as db:
        async with db.execute(f"SELECT * FROM {table}") as cursor:
            async for row in cursor:
                data.append(row)
    return data