import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import mappers, mock_data
from app.cache import MemoryCache
from app.security import build_community_sign_string, sign_community_request
from app.service import ZhihuAdapterService
from app.settings import Settings


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


class ServiceTests(unittest.TestCase):
    def test_cache_hit_does_not_increment_quota(self) -> None:
        service = ZhihuAdapterService(Settings(), MemoryCache())
        first = service.hot_list(10)
        second = service.hot_list(10)
        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(first["quota"]["usedToday"], 1)
        self.assertEqual(second["quota"]["usedToday"], 1)

    def test_search_count_is_capped(self) -> None:
        service = ZhihuAdapterService(Settings(), MemoryCache())
        result = service.zhihu_search("AI Coding", 99)
        self.assertEqual(result["cache"]["key"].split(":")[-1], "10")


if __name__ == "__main__":
    unittest.main()
