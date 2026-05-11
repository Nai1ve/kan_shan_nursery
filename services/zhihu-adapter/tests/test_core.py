import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared-python"))
sys.path.insert(0, str(ROOT))

from app import mappers, mock_data
from app.cache import MemoryCache
from app.errors import QuotaExceeded, ZhihuApiError, ZhihuAuthError, ZhihuRingNotWritable
from app.live_client import ClientBundle
from app.security import build_community_sign_string, sign_community_request
from app.service import ZhihuAdapterService
from app.settings import Settings
from kanshan_shared.config import (
    CacheConfig,
    KanshanConfig,
    LoggingConfig,
    ZhihuCommunityConfig,
    ZhihuConfig,
    ZhihuDataPlatformConfig,
    ZhihuOAuthConfig,
    ZhihuQuotaConfig,
)


def _settings(provider_mode: str = "mock", **community_overrides) -> Settings:
    community_kwargs = {
        "app_key": "test-key",
        "app_secret": "test-secret",
        "writable_ring_ids": ("2029619126742656657",),
        "default_ring_id": "2029619126742656657",
    }
    community_kwargs.update(community_overrides)
    config = KanshanConfig(
        provider_mode=provider_mode,
        zhihu=ZhihuConfig(
            community=ZhihuCommunityConfig(**community_kwargs),
            oauth=ZhihuOAuthConfig(),
            data_platform=ZhihuDataPlatformConfig(access_secret="ds-secret"),
            quota=ZhihuQuotaConfig(hot_list=3, zhihu_search=5, global_search=5, direct_answer=2),
        ),
        cache=CacheConfig(backend="memory"),
        logging=LoggingConfig(jsonl_dir="output/logs-test"),
    )
    return Settings(config=config)


class SecurityTests(unittest.TestCase):
    def test_sign_string_matches_docs(self) -> None:
        sign_string = build_community_sign_string("user-token", "1760000000", "req_1", "")
        self.assertEqual(sign_string, "app_key:user-token|ts:1760000000|logid:req_1|extra_info:")

    def test_signature_is_stable(self) -> None:
        first = sign_community_request("secret", "user-token", "1760000000", "req_1", "")
        second = sign_community_request("secret", "user-token", "1760000000", "req_1", "")
        self.assertEqual(first, second)


class MapperTests(unittest.TestCase):
    def test_hot_list_mapping_generates_source_id_and_heat_score(self) -> None:
        items = mappers.map_hot_list(mock_data.hot_list())
        self.assertEqual(items[0]["sourceType"], "hot_list")
        self.assertEqual(items[0]["contentType"], "Question")
        self.assertTrue(items[0]["sourceId"])
        self.assertEqual(items[0]["heatScore"], 100)

    def test_global_search_strips_em_tags(self) -> None:
        items = mappers.map_search(mock_data.global_search("AI Coding", 1), "global_search")
        self.assertIn("单次生成", items[0]["summary"])
        self.assertNotIn("<em>", items[0]["summary"])
        self.assertIn("<em>", items[0]["rawExcerptHtml"])

    def test_story_detail_usage_notice(self) -> None:
        item = mappers.map_story_detail(mock_data.story_detail("1644038836790169600"))
        self.assertEqual(item["sourceType"], "story")
        self.assertIn("改编自知乎盐言故事", item["usageNotice"])


class ServiceCachingAndQuotaTests(unittest.TestCase):
    def test_cache_hit_does_not_increment_quota(self) -> None:
        service = ZhihuAdapterService(_settings(), MemoryCache())
        first = service.hot_list(10)
        second = service.hot_list(10)
        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(first["quota"]["usedToday"], 1)
        self.assertEqual(second["quota"]["usedToday"], 1)

    def test_search_count_is_capped(self) -> None:
        service = ZhihuAdapterService(_settings(), MemoryCache())
        result = service.zhihu_search("AI Coding", 99)
        self.assertEqual(result["cache"]["key"].split(":")[-1], "10")

    def test_quota_exceeded_raises_after_configured_limit(self) -> None:
        service = ZhihuAdapterService(_settings(), MemoryCache())
        # configured hot_list limit = 3 in _settings(); each unique query consumes 1.
        for limit in (1, 2, 3):
            service.hot_list(limit)
        with self.assertRaises(QuotaExceeded) as ctx:
            service.hot_list(7)
        self.assertEqual(ctx.exception.endpoint, "hot_list")
        self.assertEqual(ctx.exception.limit, 3)


class WritableRingGuardTests(unittest.TestCase):
    def test_publish_pin_rejects_unknown_ring(self) -> None:
        service = ZhihuAdapterService(_settings(), MemoryCache())
        with self.assertRaises(ZhihuRingNotWritable):
            service.publish_pin({"ring_id": "9999999999", "content": "test"})

    def test_publish_pin_accepts_whitelisted_ring(self) -> None:
        service = ZhihuAdapterService(_settings(), MemoryCache())
        result = service.publish_pin({"ring_id": "2029619126742656657", "content": "test"})
        self.assertEqual(result["mode"], "mock")
        self.assertEqual(result["contentToken"], "mock-pin-token")


class OAuthClientTests(unittest.TestCase):
    def test_authorize_url_built_with_required_params(self) -> None:
        settings = _settings()
        # OAuthClient relies on app_id/app_key/redirect_uri being set; otherwise
        # the URL still renders but auth-required calls raise ZhihuAuthError.
        settings.config.zhihu.oauth.app_id = "appid"
        settings.config.zhihu.oauth.app_key = "appkey"
        settings.config.zhihu.oauth.redirect_uri = "http://127.0.0.1/cb"
        bundle = ClientBundle(settings)
        url = bundle.oauth.authorize_url()
        self.assertIn("response_type=code", url)
        self.assertIn("app_id=appid", url)
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%2Fcb", url)

    def test_oauth_get_without_token_raises_auth_error(self) -> None:
        bundle = ClientBundle(_settings())
        with self.assertRaises(ZhihuAuthError):
            bundle.oauth.get("/user")


class DataPlatformOpenAIParseTests(unittest.TestCase):
    def test_direct_answer_response_parsed_into_content_and_reasoning(self) -> None:
        service = ZhihuAdapterService(_settings(), MemoryCache())
        result = service.direct_answer({"messages": [{"role": "user", "content": "test"}]})
        self.assertIn("content", result)
        self.assertIn("reasoningContent", result)
        self.assertIn("model", result)


if __name__ == "__main__":
    unittest.main()
