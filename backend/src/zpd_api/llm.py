import os

from openai import AsyncOpenAI


def deepseek_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )
