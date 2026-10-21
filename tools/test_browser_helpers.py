import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


def load_bot(filename):
    path = Path(__file__).resolve().parents[1] / "web" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULES = [load_bot(name) for name in
           ("csdn_social_automation_bot.py", "csdn_social_automation_bot1.py")]


class BrowserHelpersTests(unittest.TestCase):
    def test_find_ele_skips_hidden_match(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                hidden, visible = Mock(), Mock()
                hidden.is_displayed.return_value = False
                visible.is_displayed.return_value = True
                bot.myBrowser = Mock()
                bot.myBrowser.find_elements.return_value = [hidden, visible]
                bot.myBrowser.find_element.return_value = hidden
                self.assertIs(bot.find_ele("//*[@class='comment-content']", timeout=0.01), visible)

    def test_failed_frame_switch_does_not_report_success(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                bot.myBrowser = Mock()
                bot.myBrowser.find_elements.return_value = []
                bot.myBrowser.switch_to.frame.side_effect = RuntimeError("frame unavailable")
                bot.find_ele = Mock(return_value=Mock())
                with patch.object(module.time, "sleep"):
                    with self.assertRaises(RuntimeError):
                        bot.iframe_in("//iframe")
                self.assertFalse(bot.iframe_flag)

    def test_already_liked_article_is_not_clicked(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                bot.myBrowser = Mock(current_url='https://blog.csdn.net/test/article/details/123')
                bot.state['articles'][bot.myBrowser.current_url] = {'comment': 'confirmed'}
                element = Mock()
                def locate(xpath, timeout=15):
                    if "@style" in xpath:
                        return None
                    return element
                bot.find_ele = Mock(side_effect=locate)
                with patch.object(module.time, "sleep"):
                    self.assertTrue(bot.csdn_dian_ping())
                element.click.assert_not_called()
                self.assertEqual(bot.dianNum, 0)

    def test_frame_waits_for_chat_list_before_success(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                bot.myBrowser = Mock()
                bot.myBrowser.find_elements.return_value = []
                frame_element, list_element = Mock(), Mock()
                bot.myBrowser.find_element.side_effect = [frame_element, list_element]
                self.assertTrue(bot.iframe_in("//iframe"))
                self.assertTrue(bot.iframe_flag)
                bot.myBrowser.switch_to.frame.assert_called_once_with(frame_element)
                calls = bot.myBrowser.find_element.call_args_list
                self.assertIn("im.csdn.net", calls[0].args[1])
                self.assertEqual(calls[1].args[1], ".main-chat-list")

    def test_frame_waits_for_outer_loading_mask_before_switch(self):
        for module in MODULES:
            bot = module.CSDN()
            bot.myBrowser = Mock()
            mask = Mock()
            mask.is_displayed.side_effect = [True, False]
            bot.myBrowser.find_elements.return_value = [mask]
            def switch(frame):
                self.assertEqual(mask.is_displayed.call_count, 2)
            bot.myBrowser.switch_to.frame.side_effect = switch
            self.assertTrue(bot.iframe_in('//iframe'))


if __name__ == "__main__":
    unittest.main()
