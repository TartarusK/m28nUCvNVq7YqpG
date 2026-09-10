#!/usr/bin/env python3
"""Exit 0 when at least one configured TikTok user is live.

The script intentionally uses the unofficial TikTokLive client because TikTok's
public developer API does not expose a general LIVE-status webhook/API.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass

from TikTokLive import TikTokLiveClient


@dataclass
class Result:
    username: str
    live: bool
    error: str | None = None


async def check(username: str) -> Result:
    username = username.lstrip("@").strip()
    client = TikTokLiveClient(unique_id=username)
    try:
        return Result(username=username, live=await client.is_live())
    except Exception as exc:  # one account failing must not hide other accounts
        return Result(username=username, live=False, error=f"{type(exc).__name__}: {exc}")
    finally:
        close = getattr(client, "close", None)
        if close:
            value = close()
            if asyncio.iscoroutine(value):
                await value


async def main(users: list[str]) -> int:
    results = await asyncio.gather(*(check(user) for user in users))
    print(json.dumps([asdict(item) for item in results], ensure_ascii=False))
    return 0 if any(item.live for item in results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("users", nargs="+", help="TikTok usernames, with or without @")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.users)))
