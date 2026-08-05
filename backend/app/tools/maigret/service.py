import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

from app.config import settings
from app.core.tool_base import NormalizedFinding
from app.models.finding import ExposureCategory

# Platforms that are ALWAYS kept if found (major social networks)
HIGH_VALUE_PLATFORMS = {
    "Instagram", "Facebook", "Twitter", "X", "YouTube", "TikTok", "LinkedIn",
    "GitHub", "GitLab", "Snapchat", "Pinterest", "Reddit", "Twitch", "Discord",
    "Telegram", "Bluesky", "Threads", "Medium", "Substack", "SoundCloud",
    "Spotify", "Steam", "DeviantART", "Behance", "Dribbble", "Figma",
    "Paypal", "Patreon", "BuyMeACoffee", "Ko-fi", "OnlyFans",
    "Wikipedia", "StackOverflow", "LeetCode", "Duolingo", "MyAnimeList",
    "Last.fm", "Bandcamp", "Imgur", "VSCO", "Blogger",
}

# Platforms that are usually just search redirects / no real profiles
LOW_VALUE_PLATFORMS = {
    "OP.GG LoL Taiwan", "OP.GG LoL Japan", "OP.GG LoL LAN", "OP.GG LoL Turkey",
    "OP.GG LoL Vietnam", "OP.GG LoL Europe West", "OP.GG LoL Europe Nordic & East",
    "OP.GG LoL North America", "OP.GG LoL Thailand", "OP.GG LoL Oceania",
    "OP.GG LoL Phillippines", "OP.GG LoL Brazil", "OP.GG LoL Russia",
    "OP.GG LoL Singapore", "CNET", "Pbase", "Instapaper", "DigitalPoint",
    "Lobsters", "Salon24.pl", "Picturepush.com", "GaiaOnline", "Domestika.org",
    "Tinkoff Invest", "Bit.ly", "Genius", "Codepen", "ThemeForest", "Codecanyon",
    "VideoHive", "Audiojungle", "Freelancer.com", "Fiverr", "Kwork",
    "Geocaching", "Gog", "AnimeNewsNetwork", "JeuxVideo", "Ccm", "Speedrun.com",
    "ArchiveOfOurOwn", "Smule", "Gitee", "Memrise", "InterPals", "Chatujme.cz",
    "Zora", "Atcoder", "Myinstants", "TheSimsResource", "OpenSea",
}

SEARCH_URL_PATTERNS = [
    "search?q=", "summoners/search", "users/filter", "/members/?username=",
    "profiles/", "/p/", "/u/", "user.aspx?username=",
]


def calculate_usefulness(result: dict[str, Any]) -> int:
    """Score a result 0-100 based on how useful/real it is."""
    score = 0
    platform = result.get("platform", "")
    ids = result.get("raw_ids", {}) or {}
    url = result.get("url_user", "")

    follower_count = ids.get("follower_count")
    try:
        if isinstance(follower_count, str):
            follower_count = int(follower_count.replace(",", ""))
        elif follower_count is None:
            follower_count = 0
        follower_count = int(follower_count)
    except (ValueError, TypeError):
        follower_count = 0

    if ids.get("fullname"): score += 15
    if ids.get("bio"): score += 15
    if ids.get("image"): score += 10
    if follower_count > 0: score += 10
    if ids.get("is_verified"): score += 10

    if platform in HIGH_VALUE_PLATFORMS:
        score += 30
    elif platform in LOW_VALUE_PLATFORMS:
        score -= 20
    else:
        score += 10

    if any(pattern in url for pattern in SEARCH_URL_PATTERNS):
        score -= 15
    if url.endswith(f"/{result.get('username', '')}"):
        score += 5
    if "api." in url or "graphql" in url:
        score -= 5

    return max(0, score)


def _run_sync(username: str, min_score: int) -> list[NormalizedFinding]:
    """
    min_score: 0 = keep everything, 15 = filter noise (recommended), 30 = only rich profiles
    """
    temp_dir = tempfile.mkdtemp(prefix="maigret_")
    try:
        cmd = [
            *settings.maigret_cmd.split(),
            username,
            "--json", "simple",
            "--folderoutput", temp_dir,
            "--dns-resolver", "threaded",
            "--no-recursion",
            "--no-color",
        ]

        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                encoding="utf-8", errors="replace", env=env,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Maigret command '{settings.maigret_cmd}' not found. "
                "Install it or set MAIGRET_CMD in your .env."
            )

        if result.returncode != 0 and "Too many errors" not in result.stderr:
            raise RuntimeError(f"Maigret failed: {result.stderr}")

        report_path = os.path.join(temp_dir, f"report_{username}_simple.json")
        if not os.path.exists(report_path):
            return []

        with open(report_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        raw_findings = []
        for platform_name, platform_data in data.items():
            status = platform_data.get("status", {})
            if status.get("status") != "Claimed":
                continue
            ids = status.get("ids", {}) or {}
            raw = {
                "username": platform_data.get("username", ""),
                "platform": platform_name,
                "url_main": platform_data.get("url_main", ""),
                "url_user": platform_data.get("url_user", ""),
                "http_status": platform_data.get("http_status"),
                "is_similar": platform_data.get("is_similar", False),
                "rank": platform_data.get("rank"),
                "tags": status.get("tags", []),
                "fullname": ids.get("fullname"),
                "bio": ids.get("bio"),
                "image": ids.get("image"),
                "follower_count": ids.get("follower_count"),
                "following_count": ids.get("following_count"),
                "is_verified": ids.get("is_verified"),
                "is_private": ids.get("is_private"),
                "is_business": ids.get("is_business"),
                "external_url": ids.get("external_url"),
                "facebook_uid": ids.get("facebook_uid"),
                "extractor": ids.get("_extractor"),
                "raw_ids": ids,
            }
            raw["usefulness_score"] = calculate_usefulness(raw)
            raw_findings.append(raw)

        filtered = [r for r in raw_findings if r["usefulness_score"] >= min_score]
        filtered.sort(key=lambda x: (-x["usefulness_score"], x["platform"]))

        http_status = None
        findings: list[NormalizedFinding] = []
        for r in filtered:
            hs = r.get("http_status")
            findings.append(
                NormalizedFinding(
                    source=r["platform"],
                    source_url=r["url_user"],
                    raw_value=r["username"],
                    category=ExposureCategory.PERSONAL_IDENTIFIER,
                    http_status=int(hs) if isinstance(hs, (int, str)) and str(hs).isdigit() else None,
                    extra_metadata={
                        "url_main": r["url_main"],
                        "tags": r.get("tags", []),
                        "rank": r.get("rank"),
                        "is_similar": r.get("is_similar"),
                        "fullname": r.get("fullname"),
                        "bio": r.get("bio"),
                        "image": r.get("image"),
                        "follower_count": r.get("follower_count"),
                        "following_count": r.get("following_count"),
                        "is_verified": r.get("is_verified"),
                        "is_private": r.get("is_private"),
                        "is_business": r.get("is_business"),
                        "external_url": r.get("external_url"),
                        "facebook_uid": r.get("facebook_uid"),
                        "extractor": r.get("extractor"),
                        "usefulness_score": r.get("usefulness_score"),
                        "raw_ids": r.get("raw_ids"),
                    },
                )
            )
        return findings
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def run(username: str, min_score: int = 15) -> list[NormalizedFinding]:
    return await asyncio.to_thread(_run_sync, username, min_score)
