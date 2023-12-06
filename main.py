import asyncio

from modules.manager import Manager


async def main():
    await Manager.menu()


if __name__ == "__main__":
    asyncio.run(main=main())
