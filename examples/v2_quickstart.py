#!/usr/bin/env python3
"""Microsoft Foundry 기본 V2 예제."""

import asyncio

from pronunciation_mapper import AgenticPronunciationMapper


async def main():
    async with AgenticPronunciationMapper(
        ["XPN36", "account_no", "transaction", "server", "log"],
        custom_mappings={
            "엑스피엔36": "XPN36",
            "어카운트넘버": "account_no",
            "서버": "server",
            "로그": "log",
        },
    ) as mapper:
        result = await mapper.rewrite(
            "엑스피엔36 서버에서 어카운트넘버 사삼삼오삼칠의 트랜잭숑 로그"
        )
        print(result.rewritten_text)
        print(result.to_dict())


if __name__ == "__main__":
    asyncio.run(main())
