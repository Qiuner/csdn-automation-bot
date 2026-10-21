import unittest
from unittest.mock import Mock, patch

from playwright.sync_api import TimeoutError as PlaywrightTimeout

from check_dom import inspect_page


class DomDiagnosticsTests(unittest.TestCase):
    def test_login_redirect_is_not_reported_as_dom_change(self):
        page = Mock(url="https://passport.csdn.net/login?token=private", frames=[])
        page.goto.return_value.status = 200
        with patch("check_dom.SELECTORS", {}):
            report = inspect_page(page, "https://i.csdn.net/#/msg/chat")
        self.assertTrue(report["login_required"])
        self.assertNotIn("token", report["page_path"])

    def test_timeout_still_inspects_loaded_frames(self):
        frame = Mock(url="https://im.csdn.net/ichat?token=private")
        frame.locator.return_value.evaluate_all.return_value = {"count": 2, "visible": 1}
        page = Mock(url="https://i.csdn.net/#/msg/chat", frames=[frame])
        page.goto.side_effect = PlaywrightTimeout("slow page")
        with patch("check_dom.SELECTORS", {"chat_item": ".msg-item_inner"}):
            report = inspect_page(page, page.url)
        self.assertTrue(report["navigation_timeout"])
        self.assertEqual(report["frames"][0]["selectors"]["chat_item"],
                         {"count": 2, "visible": 1})
        self.assertNotIn("token", report["frames"][0]["path"])

    def test_http_error_status_is_preserved(self):
        page = Mock(url="https://blog.csdn.net/example/article/details/1", frames=[])
        page.goto.return_value.status = 403
        report = inspect_page(page, page.url)
        self.assertEqual(report["status"], 403)
        self.assertFalse(report["navigation_timeout"])


if __name__ == "__main__":
    unittest.main()
