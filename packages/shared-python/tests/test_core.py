import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kanshan_shared import KanshanConfig, configure_logging, get_logger, load_config
from kanshan_shared._yaml import parse_yaml
from kanshan_shared.logger import reset_for_tests


def write_yaml(tmp: pathlib.Path, body: str) -> pathlib.Path:
    path = tmp / "config.yaml"
    path.write_text(body, encoding="utf-8")
    return path


class YamlParserTests(unittest.TestCase):
    def test_parse_nested_mapping_and_list(self) -> None:
        text = """
zhihu:
  community:
    app_key: "abc"
    writable_ring_ids:
      - "111"
      - "222"
    base_url: https://openapi.zhihu.com
""".strip("\n")
        parsed = parse_yaml(text)
        self.assertEqual(parsed["zhihu"]["community"]["app_key"], "abc")
        self.assertEqual(parsed["zhihu"]["community"]["writable_ring_ids"], ["111", "222"])
        self.assertEqual(parsed["zhihu"]["community"]["base_url"], "https://openapi.zhihu.com")

    def test_inline_comment_is_stripped(self) -> None:
        parsed = parse_yaml("key: value # trailing")
        self.assertEqual(parsed["key"], "value")

    def test_coerce_bool_int_float_null(self) -> None:
        parsed = parse_yaml("a: true\nb: 42\nc: 1.5\nd: null\ne:")
        self.assertIs(parsed["a"], True)
        self.assertEqual(parsed["b"], 42)
        self.assertEqual(parsed["c"], 1.5)
        self.assertIsNone(parsed["d"])
        self.assertIsNone(parsed["e"])


class ConfigLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        for env in [
            "KANSHAN_CONFIG_PATH",
            "ZHIHU_APP_KEY",
            "ZHIHU_APP_SECRET",
            "ZHIHU_ACCESS_TOKEN",
            "ZHIHU_ACCESS_SECRET",
            "PROVIDER_MODE",
            "ZHIHU_PROVIDER_MODE",
        ]:
            os.environ.pop(env, None)

    def test_loads_nested_yaml_into_dataclasses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = write_yaml(
                pathlib.Path(tmp),
                """
provider_mode: live
zhihu:
  community:
    app_key: roach-7
    app_secret: secret
    writable_ring_ids:
      - "111"
      - "222"
    default_ring_id: "111"
  data_platform:
    access_secret: ds_secret
    default_model: zhida-fast-1p5
  quota:
    hot_list: 50
""",
            )
            config = load_config(cfg_path)
        self.assertEqual(config.provider_mode, "live")
        self.assertEqual(config.zhihu.community.app_key, "roach-7")
        self.assertEqual(config.zhihu.community.writable_ring_ids, ("111", "222"))
        self.assertEqual(config.zhihu.community.default_ring_id, "111")
        self.assertEqual(config.zhihu.data_platform.access_secret, "ds_secret")
        self.assertEqual(config.zhihu.data_platform.default_model, "zhida-fast-1p5")
        self.assertEqual(config.zhihu.quota.hot_list, 50)

    def test_legacy_flat_schema_maps_to_community(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = write_yaml(
                pathlib.Path(tmp),
                """
zhihu:
  ZHIHU_APP_KEY: roach-7
  ZHIHU_APP_SECRET: secret-xyz
""",
            )
            config = load_config(cfg_path)
        self.assertEqual(config.zhihu.community.app_key, "roach-7")
        self.assertEqual(config.zhihu.community.app_secret, "secret-xyz")

    def test_env_overrides_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = write_yaml(
                pathlib.Path(tmp),
                """
zhihu:
  community:
    app_key: file-key
""",
            )
            os.environ["ZHIHU_APP_KEY"] = "env-key"
            try:
                config = load_config(cfg_path)
            finally:
                os.environ.pop("ZHIHU_APP_KEY", None)
        self.assertEqual(config.zhihu.community.app_key, "env-key")

    def test_missing_file_returns_defaults(self) -> None:
        config = load_config(pathlib.Path("/nonexistent/path/config.yaml"))
        self.assertIsInstance(config, KanshanConfig)
        self.assertEqual(config.provider_mode, "mock")
        self.assertEqual(config.zhihu.community.app_key, "")


class LoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()

    def tearDown(self) -> None:
        reset_for_tests()

    def test_jsonl_record_contains_event_and_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            configure_logging("test-service", _logging_cfg(tmp, "DEBUG"))
            logger = get_logger("kanshan.test")
            logger.info("zhihu_call_started", extra={"requestId": "req-1", "endpoint": "hot_list"})
            logger.error("zhihu_call_failed", extra={"requestId": "req-1", "errorCode": 30001})

            files = list(pathlib.Path(tmp).glob("test-service-*.jsonl"))
            self.assertEqual(len(files), 1)
            lines = files[0].read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            self.assertEqual(first["service"], "test-service")
            self.assertEqual(first["level"], "INFO")
            self.assertEqual(first["event"], "zhihu_call_started")
            self.assertEqual(first["requestId"], "req-1")
            self.assertEqual(first["endpoint"], "hot_list")
            second = json.loads(lines[1])
            self.assertEqual(second["level"], "ERROR")
            self.assertEqual(second["errorCode"], 30001)

    def test_no_crash_when_directory_unwritable(self) -> None:
        configure_logging("test-service", _logging_cfg("/proc/cannot-write-here", "INFO"))
        logger = get_logger("kanshan.test")
        # must not raise even if jsonl dir cannot be created
        logger.info("should_not_crash")


def _logging_cfg(jsonl_dir, console_level):
    class _Cfg:
        pass
    cfg = _Cfg()
    cfg.jsonl_dir = jsonl_dir
    cfg.console_level = console_level
    return cfg


if __name__ == "__main__":
    unittest.main()
