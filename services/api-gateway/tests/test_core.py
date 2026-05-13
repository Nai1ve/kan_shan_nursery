import pathlib
import sys
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED_ROOT = ROOT.parents[1] / "packages" / "shared-python"
sys.path.insert(0, str(SHARED_ROOT))
sys.path.insert(0, str(ROOT))

from app.errors import DownstreamHttpError, ServiceNotReady
from app.service import GatewayService
from app.settings import Settings


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: dict[tuple[str, str, str], tuple[int, Any]] = {}

    def add(self, method: str, base_url: str, path: str, status_code: int, data: Any) -> None:
        self.responses[(method.upper(), base_url, path)] = (status_code, data)

    def request(
        self,
        method: str,
        service_name: str,
        base_url: str,
        path: str,
        request_id: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float = 20,
        session_id: str | None = None,
    ) -> tuple[int, Any]:
        self.calls.append(
            {
                "method": method.upper(),
                "service": service_name,
                "base_url": base_url,
                "path": path,
                "request_id": request_id,
                "params": params,
                "payload": payload,
                "timeout": timeout_seconds,
                "session_id": session_id,
            }
        )
        return self.responses.get((method.upper(), base_url, path), (200, {"ok": True}))


def settings(ready_services: set[str] | None = None) -> Settings:
    return Settings(
        profile_service_url="http://profile",
        content_service_url="http://content",
        seed_service_url="http://seed",
        sprout_service_url="http://sprout",
        writing_service_url="http://writing",
        feedback_service_url="http://feedback",
        zhihu_adapter_url="http://zhihu",
        llm_service_url="http://llm",
        ready_services=frozenset(ready_services or {"profile", "seed", "llm", "zhihu", "content", "sprout", "writing", "feedback"}),
    )


class GatewayServiceTests(unittest.TestCase):
    def test_health_reports_ready_downstreams(self) -> None:
        service = GatewayService(settings({"profile", "seed", "llm", "zhihu"}), FakeClient())

        response = service.health("req-test")

        self.assertEqual(response["request_id"], "req-test")
        self.assertTrue(response["data"]["downstream"]["profile"]["ready"])
        self.assertFalse(response["data"]["downstream"]["content"]["ready"])

    def test_proxy_wraps_success_and_propagates_request_id(self) -> None:
        fake = FakeClient()
        fake.add("GET", "http://profile", "/profiles/me", 200, {"nickname": "看山编辑"})
        service = GatewayService(settings(), fake)

        response = service.proxy("req-1", "profile", "GET", "/profiles/me")

        self.assertEqual(response["request_id"], "req-1")
        self.assertEqual(response["data"]["nickname"], "看山编辑")
        self.assertEqual(fake.calls[0]["request_id"], "req-1")
        self.assertEqual(fake.calls[0]["service"], "profile")

    def test_proxy_passes_payload_and_query_params(self) -> None:
        fake = FakeClient()
        service = GatewayService(settings(), fake)

        service.proxy("req-2", "seed", "POST", "/seeds/from-card", {"debug": "1"}, {"cardId": "card-1"})

        self.assertEqual(fake.calls[0]["params"], {"debug": "1"})
        self.assertEqual(fake.calls[0]["payload"], {"cardId": "card-1"})

    def test_unready_service_raises_service_not_ready(self) -> None:
        service = GatewayService(settings({"profile"}), FakeClient())

        with self.assertRaises(ServiceNotReady) as context:
            service.proxy("req-3", "content", "GET", "/content")

        self.assertEqual(context.exception.code, "SERVICE_NOT_READY")
        self.assertEqual(context.exception.status_code, 503)

    def test_downstream_error_is_normalized(self) -> None:
        fake = FakeClient()
        fake.add("GET", "http://seed", "/seeds/missing", 404, {"detail": {"code": "SEED_NOT_FOUND"}})
        service = GatewayService(settings(), fake)

        with self.assertRaises(DownstreamHttpError) as context:
            service.proxy("req-4", "seed", "GET", "/seeds/missing")

        self.assertEqual(context.exception.code, "DOWNSTREAM_ERROR")
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail["service"], "seed")


if __name__ == "__main__":
    unittest.main()
