import unittest
from unittest.mock import Mock, patch

from test_browser_helpers import MODULES


class RewardTests(unittest.TestCase):
    def test_community_open_popup_confirms_class_based_receipt(self):
        for module in MODULES:
            bot = module.CSDN()
            bot.myBrowser = Mock()
            card, popup, button, receipt = Mock(), Mock(), Mock(), Mock()
            card.get_attribute.side_effect = lambda name: 'redpack-card' if name == 'class' else None
            receipt.text = '0.12元'
            def locate(xpath, timeout=15):
                if 'redpack-card' in xpath:
                    return card
                if xpath == "//*[@class='env-box']":
                    return popup
                if 'red-openbtn' in xpath:
                    self.assertNotIn("@id='preOpen'", xpath)
                    return button
                if 'my-receive' in xpath:
                    self.assertNotIn("@id='opened'", xpath)
                    return receipt if button.click.called else None
                return None
            bot.find_ele = Mock(side_effect=locate)
            self.assertTrue(bot.csdn_hong_bao())
            card.click.assert_not_called()
            button.click.assert_called_once()
            self.assertEqual(bot.hongNum, 1)

    def test_community_overdue_class_skips_claim(self):
        for module in MODULES:
            bot = module.CSDN()
            card = Mock()
            card.get_attribute.side_effect = lambda name: 'redpack-card redpack-card-overdue' if name == 'class' else None
            bot.find_ele = Mock(return_value=card)
            self.assertFalse(bot.csdn_hong_bao())
            card.click.assert_not_called()

    def test_open_sidebar_uses_its_card_and_waits_for_status(self):
        for module in MODULES:
            bot = module.CSDN()
            bot.myBrowser = Mock(current_url='https://blog.csdn.net/test/article/details/1#comments_2')
            entry, shadow, card = Mock(), Mock(), Mock()
            statuses = iter([None, 'completed', 'completed'])
            card.get_attribute.side_effect = lambda name: next(statuses, 'completed')
            def locate(xpath, timeout=15):
                if 'commentSideBoxshadow' in xpath:
                    return shadow
                if 'tool-item-comment' in xpath:
                    return entry
                if 'pcCommentSideBox' in xpath and 'comment-reward-item' in xpath:
                    return card
                if 'comment-reward-item' in xpath:
                    self.fail('Must not select covered background reward')
                return None
            bot.find_ele = Mock(side_effect=locate)
            self.assertFalse(bot.csdn_hong_bao())
            entry.click.assert_not_called()
            card.click.assert_not_called()
            self.assertEqual(bot.hongNum, 0)

    def test_dry_run_never_opens_reward(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                card = Mock()
                card.get_attribute.return_value = None
                bot.find_ele = Mock(return_value=card)
                self.assertFalse(bot.csdn_hong_bao(dry_run=True))
                card.click.assert_not_called()
                self.assertEqual(bot.hongNum, 0)

    def test_list_navigation_preserves_existing_tabs(self):
        for module in MODULES:
            for new_tab in (False, True):
                with self.subTest(module=module.__name__, new_tab=new_tab):
                    bot = module.CSDN()
                    driver = Mock()
                    driver.current_window_handle = "list"
                    driver.window_handles = ["list", "unrelated"]
                    driver.current_url = module.csdn_hongbao_url
                    icon = Mock()
                    driver.find_element.return_value = icon
                    driver.find_elements.return_value = [icon]
                    driver.execute_script.return_value = "complete"
                    def navigate(url):
                        driver.current_url = url
                    def click():
                        if new_tab:
                            driver.window_handles.append("reward")
                        else:
                            driver.current_url = "https://blog.csdn.net/test/article/details/1"
                    def switch(handle):
                        driver.current_window_handle = handle
                        if handle == "reward":
                            driver.current_url = "https://blog.csdn.net/test/article/details/1"
                        elif handle == "list" and new_tab:
                            driver.current_url = module.csdn_hongbao_url
                    driver.get.side_effect = navigate
                    driver.switch_to.window.side_effect = switch
                    driver.close.side_effect = lambda: driver.window_handles.remove(driver.current_window_handle)
                    icon.click.side_effect = click
                    bot.myBrowser = driver
                    bot.csdn_hong_bao = Mock(return_value=False)
                    bot.csdn_dian_ping = Mock()
                    def wait_once(condition):
                        result = condition(driver)
                        if not result:
                            raise module.TimeoutException()
                        return result
                    with patch.object(module, "WebDriverWait") as wait:
                        wait.return_value.until.side_effect = wait_once
                        self.assertFalse(bot.csdn_hu_hong_bao(dry_run=True))
                    bot.csdn_hong_bao.assert_called_once_with(dry_run=True)
                    bot.csdn_dian_ping.assert_not_called()
                    self.assertEqual(driver.window_handles, ["list", "unrelated"])
                    self.assertEqual(driver.current_window_handle, "list")
                    self.assertEqual(driver.current_url, module.csdn_hongbao_url)

    def test_no_card_is_not_success(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                bot.find_ele = Mock(return_value=None)
                bot.myBrowser = Mock()
                with patch.object(module.time, "sleep"):
                    self.assertFalse(bot.csdn_hong_bao())
                self.assertEqual(bot.hongNum, 0)

    def test_completed_reward_is_not_opened(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                for status in ("completed", "expired", "received"):
                    bot = module.CSDN()
                    card = Mock()
                    card.get_attribute.return_value = status
                    bot.find_ele = Mock(return_value=card)
                    bot.myBrowser = Mock()
                    with patch.object(module.time, "sleep"):
                        self.assertFalse(bot.csdn_hong_bao())
                    card.click.assert_not_called()
                    self.assertEqual(bot.hongNum, 0)

    def test_comments_are_expanded_before_finding_reward(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                entry, card = Mock(), Mock()
                card.get_attribute.return_value = "completed"
                def locate(xpath, timeout=15):
                    if "tool-item-comment" in xpath:
                        return entry
                    if "comment-reward-item" in xpath and entry.click.called:
                        return card
                    return None
                bot.find_ele = Mock(side_effect=locate)
                bot.myBrowser = Mock()
                def click_entry():
                    bot.myBrowser.execute_script.assert_called_with(
                        "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", entry)
                entry.click.side_effect = click_entry
                with patch.object(module.time, "sleep"):
                    self.assertFalse(bot.csdn_hong_bao())
                entry.click.assert_called_once()
                card.click.assert_not_called()

    def test_click_without_result_is_not_counted(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                card, button, close = Mock(), Mock(), Mock()
                card.get_attribute.return_value = "available"
                def locate(xpath, timeout=15):
                    if "redpack-card" in xpath:
                        return card
                    if "red-openbtn" in xpath:
                        return button
                    if "close-btn" in xpath:
                        return close
                    return None
                bot.find_ele = Mock(side_effect=locate)
                bot.myBrowser = Mock()
                with patch.object(module.time, "sleep"):
                    self.assertFalse(bot.csdn_hong_bao())
                button.click.assert_called_once()
                close.click.assert_called_once()
                self.assertEqual(bot.hongNum, 0)

    def test_new_visible_receipt_counts_once(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                bot = module.CSDN()
                card, button, receipt, close = Mock(), Mock(), Mock(), Mock()
                card.get_attribute.return_value = "available"
                receipt.text = "0.01"
                def locate(xpath, timeout=15):
                    if "redpack-card" in xpath:
                        return card
                    if "my-receive" in xpath:
                        return receipt if button.click.called else None
                    if "red-openbtn" in xpath:
                        return button
                    if "close-btn" in xpath:
                        return close
                    return None
                bot.find_ele = Mock(side_effect=locate)
                bot.myBrowser = Mock()
                with patch.object(module.time, "sleep"):
                    self.assertTrue(bot.csdn_hong_bao())
                self.assertEqual(bot.hongNum, 1)
                button.click.assert_called_once()
                close.click.assert_called_once()


if __name__ == "__main__":
    unittest.main()
