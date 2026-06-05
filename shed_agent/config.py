from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("config/shed_agent_config.json")


@dataclass
class AgentConfig:
    target_locations: list[str] = field(default_factory=list)
    target_radius_miles: int = 18
    target_skus: list[str] = field(default_factory=lambda: ["4x6_horizontal", "6x5_vertical"])
    max_initial_inventory: int = 10
    preferred_initial_inventory: str = "6-8"
    craigslist_rss_urls: list[str] = field(default_factory=list)
    watchlist_urls: list[str] = field(default_factory=list)
    retail_comparable_urls: list[str] = field(default_factory=list)
    enable_facebook_marketplace_collector: bool = False
    facebook_user_data_dir: str = ".local/playwright/facebook-profile"
    facebook_search_keywords: list[str] = field(default_factory=list)
    max_listings_per_keyword: int = 20
    max_scrolls_per_keyword: int = 3
    open_detail_pages: bool = True
    max_detail_pages_per_run: int = 50
    delay_between_actions_ms: int | list[int] = field(default_factory=lambda: [1500, 3000])
    headless: bool = False
    facebook_launch_mode: str = "persistent_playwright"
    facebook_cdp_url: str = "http://127.0.0.1:9222"
    facebook_cdp_port: int = 9222
    facebook_start_chrome_for_cdp: bool = True
    facebook_chrome_executable_path: str = ""
    facebook_run_mode: str = "manual_start"
    facebook_marketplace_location_slug: str = "boston"
    facebook_manual_challenge_timeout_seconds: int = 300
    enable_llm_analysis: bool = True
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    max_llm_listings_per_run: int = 100
    max_description_chars_for_llm: int = 4000
    cache_llm_results: bool = True
    reanalyze_changed_listings_only: bool = True
    enable_image_analysis: bool = False
    llm_cache_dir: str = "data/llm_cache"
    routine: dict[str, object] = field(default_factory=dict)
    logging: dict[str, object] = field(default_factory=dict)
    score_thresholds: dict[str, float] = field(default_factory=dict)
    provisional_target_prices: dict[str, float] = field(default_factory=dict)
    expected_landed_cost_placeholders: dict[str, float] = field(default_factory=dict)
    report_output_directory: str = "data/reports"
    observation_window_start_date: str = ""
    observation_window_days: int = 7
    dashboard_output_file: str = "reports/dashboard.html"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AgentConfig:
    if not path.exists():
        return AgentConfig()
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    return AgentConfig(
        target_locations=data.get("targetLocations", []),
        target_radius_miles=data.get("targetRadiusMiles", 18),
        target_skus=data.get("targetSkus", ["4x6_horizontal", "6x5_vertical"]),
        max_initial_inventory=data.get("maxInitialInventory", 10),
        preferred_initial_inventory=data.get("preferredInitialInventory", "6-8"),
        craigslist_rss_urls=data.get("craigslistRssUrls", []),
        watchlist_urls=_normalize_watchlist_urls(data.get("watchlistUrls", [])),
        retail_comparable_urls=_normalize_watchlist_urls(data.get("retailComparableUrls", [])),
        enable_facebook_marketplace_collector=data.get("enableFacebookMarketplaceCollector", False),
        facebook_user_data_dir=data.get("facebookUserDataDir", ".local/playwright/facebook-profile"),
        facebook_search_keywords=data.get("facebookSearchKeywords", []),
        max_listings_per_keyword=data.get("maxListingsPerKeyword", 20),
        max_scrolls_per_keyword=data.get("maxScrollsPerKeyword", 3),
        open_detail_pages=data.get("openDetailPages", True),
        max_detail_pages_per_run=data.get("maxDetailPagesPerRun", 50),
        delay_between_actions_ms=data.get("delayBetweenActionsMs", [1500, 3000]),
        headless=data.get("headless", False),
        facebook_launch_mode=data.get("facebookLaunchMode", "persistent_playwright"),
        facebook_cdp_url=data.get("facebookCdpUrl", "http://127.0.0.1:9222"),
        facebook_cdp_port=data.get("facebookCdpPort", 9222),
        facebook_start_chrome_for_cdp=data.get("facebookStartChromeForCdp", True),
        facebook_chrome_executable_path=data.get("facebookChromeExecutablePath", ""),
        facebook_run_mode=data.get("facebookRunMode", "manual_start"),
        facebook_marketplace_location_slug=data.get("facebookMarketplaceLocationSlug", "boston"),
        facebook_manual_challenge_timeout_seconds=data.get("facebookManualChallengeTimeoutSeconds", 300),
        enable_llm_analysis=data.get("enableLLMAnalysis", True),
        llm_provider=data.get("llmProvider", "openai"),
        llm_model=data.get("llmModel", "gpt-4.1-mini"),
        max_llm_listings_per_run=data.get("maxLLMListingsPerRun", 100),
        max_description_chars_for_llm=data.get("maxDescriptionCharsForLLM", 4000),
        cache_llm_results=data.get("cacheLLMResults", True),
        reanalyze_changed_listings_only=data.get("reanalyzeChangedListingsOnly", True),
        enable_image_analysis=data.get("enableImageAnalysis", False),
        llm_cache_dir=data.get("llmCacheDir", "data/llm_cache"),
        routine=data.get("routine", {}),
        logging=data.get("logging", {}),
        score_thresholds=data.get("scoreThresholds", {}),
        provisional_target_prices=data.get("provisionalTargetPrices", {}),
        expected_landed_cost_placeholders=data.get("expectedLandedCostPlaceholders", {}),
        report_output_directory=data.get("reportOutputDirectory", "data/reports"),
        observation_window_start_date=data.get("observationWindowStartDate", ""),
        observation_window_days=data.get("observationWindowDays", 7),
        dashboard_output_file=data.get("dashboardOutputFile", "reports/dashboard.html"),
    )


def _normalize_watchlist_urls(values: list[Any]) -> list[str]:
    urls = []
    for value in values:
        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, dict) and value.get("url"):
            urls.append(value["url"])
    return urls
