import asyncio
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(api_key="")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            max_completion_tokens=20,
        )
        print(response.choices[0].message.content)

    except Exception as e:
        print(type(e).__name__)
        print(e)

asyncio.run(main())