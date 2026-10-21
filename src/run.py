import asyncio


async def main():
    print('Hello World')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit.')
