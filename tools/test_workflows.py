import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_browser_helpers import MODULES

ARTICLE = 'https://blog.csdn.net/test/article/details/123'


class WorkflowTests(unittest.TestCase):
    def test_startup_restores_account_state_and_uses_one_browser(self):
        for module in MODULES:
            with tempfile.TemporaryDirectory() as directory:
                driver = Mock()
                driver.get_cookie.return_value = {'value': 'test-account'}
                with patch.object(module, 'BrowserWebDriver', return_value=driver) as create, patch('builtins.input'):
                    first = module.CSDN(data_dir=directory)
                    first.start_browser()
                    first.state['count'] = 17
                    first.state['articles'][ARTICLE] = {'comment': 'pending'}
                    first.save_state()
                    self.assertEqual(create.call_count, 1)
                    driver.quit.assert_not_called()
                    second = module.CSDN(data_dir=directory)
                    second.start_browser()
                    self.assertEqual(second.dianNum, 17)
                    self.assertEqual(second.state['articles'][ARTICLE]['comment'], 'pending')
                    self.assertEqual(first.state_path, second.state_path)
                    driver.get_cookie.return_value = {'value': 'other-account'}
                    third = module.CSDN(data_dir=directory)
                    third.start_browser()
                    self.assertNotEqual(first.state_path, third.state_path)
                    self.assertEqual(third.dianNum, 0)

    def test_explicit_missing_browser_is_reported(self):
        for module in MODULES:
            with tempfile.TemporaryDirectory() as directory:
                (Path(directory) / 'config.txt').write_text('CHROME_BROWSER_PATH = "missing.exe"')
                with patch.object(module, 'BrowserWebDriver') as create:
                    with self.assertRaises(FileNotFoundError):
                        module.CSDN(data_dir=directory).start_browser()
                    create.assert_not_called()

    def test_chat_skips_bad_links_and_does_not_loop_on_unread_item(self):
        routes = [
            ('https://im.csdn.net/ichat/test-user', True),
            ('https://im.csdn.net/chat/test-user?source=test', True),
            ('https://im.csdn.net/ichat/#/chat/test-user', True),
            ('https://im.csdn.net/ichat', False),
            ('https://im.csdn.net/ichat/notice/system', False),
            ('https://example.com/ichat/test-user', False),
        ]
        for module, (frame_url, valid) in [(m, route) for m in MODULES for route in routes]:
            bot = module.CSDN()
            driver = Mock()
            driver.execute_script.return_value = frame_url
            item = Mock()
            name, relation, marker, avatar = Mock(), Mock(), Mock(), Mock()
            name.text = 'name'
            relation.text = '好友'
            avatar.get_attribute.return_value = 'avatar'
            item.find_elements.side_effect = lambda by, selector: {
                '.unread-num': [marker], '.who-msg': [name],
                '.msg-relation': [relation], '.headimg img': [avatar],
            }.get(selector, [item])
            links = []
            for href in ['https://evil.test/', ARTICLE, ARTICLE + '?spm=x']:
                link = Mock()
                link.get_attribute.return_value = href
                links.append(link)
            list_reads = 0
            def elements(by, selector):
                nonlocal list_reads
                if selector == '.main-chat-list .msg-item_inner':
                    list_reads += 1
                    if list_reads == 1:
                        return []
                    return [item]
                if selector == '.msg-content-box .loading':
                    return []
                return links
            driver.find_elements.side_effect = elements
            bot.myBrowser = driver
            bot.find_ele = Mock(return_value=Mock())
            bot.iframe_in = Mock()
            bot.iframe_out = Mock()
            bot.visit_article = Mock(return_value=True)
            bot.send_chat_message = Mock(return_value=True)
            self.assertTrue(bot.csdn_hu_chat())
            item.click.assert_called_once()
            if valid:
                bot.visit_article.assert_called_once_with(ARTICLE, '聊天')
                bot.send_chat_message.assert_called_once()
            else:
                bot.visit_article.assert_not_called()
                bot.send_chat_message.assert_not_called()
            bot.iframe_out.assert_called_once()

    def test_configuration_is_anchored_and_literal_only(self):
        for module in MODULES:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'config.txt'
                path.write_text('CHROME_BROWSER_PATH = "browser.exe"', encoding='utf-8')
                bot = module.CSDN(data_dir=directory)
                self.assertEqual(bot.config['CHROME_BROWSER_PATH'], 'browser.exe')
                self.assertEqual(module.CSDN().curDir, str(Path(module.__file__).resolve().parent))
                path.write_text('CHROME_BROWSER_PATH = __import__("os")', encoding='utf-8')
                with self.assertRaises(ValueError):
                    module.CSDN(data_dir=directory)

    def test_chat_distinguishes_identical_profiles_and_skips_loading_timeout(self):
        for module in MODULES:
            for stalled, dry_run in ((False, False), (True, False), (False, True)):
                with self.subTest(module=module.__name__, stalled=stalled, dry_run=dry_run):
                    bot = module.CSDN()
                    driver = bot.myBrowser = Mock()
                    route = 'https://im.csdn.net/ichat'
                    items = []
                    for number in (1, 2):
                        item = Mock(id=f'element-{number}')
                        name, relation, avatar = Mock(), Mock(), Mock()
                        name.text = 'same-name' if not stalled else str(number)
                        relation.text = '好友'
                        avatar.get_attribute.return_value = 'default-avatar'
                        fields = {'.unread-num': [Mock()], '.who-msg': [name],
                                  '.msg-relation': [relation], '.headimg img': [avatar]}
                        item.find_elements.side_effect = lambda by, selector, fields=fields: fields.get(selector, [])
                        def click(number=number):
                            nonlocal route
                            route = f'https://im.csdn.net/ichat/user{number}'
                        item.click.side_effect = click
                        items.append(item)
                    driver.execute_script.side_effect = lambda script: route
                    links = []
                    for number in range(7):
                        link = Mock()
                        link.get_attribute.return_value = ARTICLE + str(number)
                        links.append(link)
                    def elements(by, selector):
                        if selector == '.main-chat-list .msg-item_inner':
                            return items
                        if selector == '.msg-content-box .loading':
                            return [Mock()] if stalled and route.endswith('user1') else []
                        return links
                    driver.find_elements.side_effect = elements
                    bot.find_ele = Mock(return_value=Mock())
                    bot.iframe_in = Mock()
                    bot.iframe_out = Mock()
                    bot.visit_article = Mock(return_value=True)
                    bot.send_chat_message = Mock(return_value=True)
                    def until(predicate):
                        value = predicate(driver)
                        if not value:
                            raise module.TimeoutException('conversation loading')
                        return value
                    with patch.object(module, 'WebDriverWait') as wait:
                        wait.return_value.until.side_effect = until
                        self.assertTrue(bot.csdn_hu_chat(dry_run=dry_run, max_conversations=2, max_articles=2))
                    for item in items:
                        item.click.assert_called_once()
                    if dry_run:
                        bot.visit_article.assert_not_called()
                        bot.send_chat_message.assert_not_called()
                    else:
                        self.assertEqual(bot.visit_article.call_count, 2 if stalled else 4)
                        self.assertEqual([call.args[0] for call in bot.visit_article.call_args_list[:2]],
                                         [ARTICLE + '5', ARTICLE + '6'])

    def test_url_filter_normalizes_only_articles(self):
        for module in MODULES:
            self.assertEqual(module.CSDN.article_url(ARTICLE + '?spm=x#comments_1'), ARTICLE)
            self.assertEqual(module.CSDN.article_url('https://qiuner.blog.csdn.net/article/details/157251513?spm=x'),
                             'https://qiuner.blog.csdn.net/article/details/157251513')
            self.assertIsNone(module.CSDN.article_url('https://qiuner.blog.csdn.net.evil.test/article/details/157251513'))
            for value in ['https://blog.csdn.net.evil.test/test/article/details/123',
                          'https://evil.test/', 'javascript:alert(1)', 'https://blog.csdn.net/test',
                          'https://user@blog.csdn.net/test/article/details/123', None]:
                self.assertIsNone(module.CSDN.article_url(value))

    def test_daily_limit_and_rollover_preserve_pending(self):
        for module in MODULES:
            with tempfile.TemporaryDirectory() as directory:
                bot = module.CSDN(data_dir=directory)
                bot.state_path = Path(directory) / 'state.json'
                bot.dianNum = bot.state['count'] = 50
                self.assertFalse(bot.refresh_daily_limit())
                bot.state['articles'][ARTICLE] = {'comment': 'pending'}
                bot.state['date'] = '2000-01-01'
                self.assertTrue(bot.refresh_daily_limit())
                saved = json.loads(bot.state_path.read_text(encoding='utf-8'))
                self.assertEqual(saved['count'], 0)
                self.assertEqual(saved['articles'][ARTICLE]['comment'], 'pending')

    def test_comment_result_is_persisted_and_not_repeated(self):
        for module in MODULES:
            for confirmed in (False, True):
                with self.subTest(module=module.__name__, confirmed=confirmed), tempfile.TemporaryDirectory() as directory:
                    bot = module.CSDN(data_dir=directory)
                    bot.state_path = Path(directory) / 'state.json'
                    bot.myBrowser = Mock(current_url=ARTICLE)
                    active, entry, editor, submit = Mock(), Mock(), Mock(), Mock()
                    editor.get_attribute.return_value = ''
                    def locate(xpath, timeout=15):
                        if 'commentSideBoxshadow' in xpath:
                            return None
                        if '评论成功' in xpath:
                            return active if confirmed and submit.click.called else None
                        if 'isactive' in xpath or 'is-collection-imgactive' in xpath:
                            return active
                        if 'tool-item-comment' in xpath:
                            return entry
                        if 'comment-content' in xpath:
                            return editor
                        if 'btn-comment' in xpath:
                            return submit
                        raise AssertionError(xpath)
                    bot.find_ele = Mock(side_effect=locate)
                    self.assertEqual(bot.csdn_dian_ping(comment_text='测试'), confirmed)
                    editor.send_keys.assert_called_once_with('测试')
                    saved = json.loads(bot.state_path.read_text(encoding='utf-8'))
                    self.assertEqual(saved['articles'][ARTICLE]['comment'], 'confirmed' if confirmed else 'pending')
                    self.assertEqual(saved['count'], 1)
                    self.assertEqual(bot.csdn_dian_ping(), confirmed)
                    submit.click.assert_called_once()
                    active.click.assert_not_called()
                    self.assertEqual(bot.dianNum, 1)

    def test_comment_waits_for_input_to_enable_submit_and_preserves_open_panel(self):
        for module in MODULES:
            for panel_open in (False, True):
                with self.subTest(module=module.__name__, panel_open=panel_open), tempfile.TemporaryDirectory() as directory:
                    bot = module.CSDN(data_dir=directory)
                    bot.state_path = Path(directory) / 'state.json'
                    bot.myBrowser = Mock(current_url=ARTICLE)
                    active, entry, editor, submit = Mock(), Mock(), Mock(), Mock()
                    editor.get_attribute.return_value = ''
                    submit.is_enabled.side_effect = lambda: editor.send_keys.called
                    def locate(xpath, timeout=15):
                        if 'commentSideBoxshadow' in xpath:
                            return active if panel_open else None
                        if '评论成功' in xpath:
                            return active if submit.click.called else None
                        if 'isactive' in xpath or 'is-collection-imgactive' in xpath:
                            return active
                        if 'tool-item-comment' in xpath:
                            return entry
                        if 'comment-content' in xpath:
                            return editor
                        if 'btn-comment' in xpath:
                            return submit
                        raise AssertionError(xpath)
                    bot.find_ele = Mock(side_effect=locate)
                    self.assertTrue(bot.csdn_dian_ping(comment_text='测试'))
                    self.assertEqual(entry.click.call_count, 0 if panel_open else 1)
                    submit.click.assert_called_once()
                    self.assertEqual(json.loads(bot.state_path.read_text())['count'], 1)

    def test_already_liked_still_attempts_collection(self):
        for module in MODULES:
            bot = module.CSDN()
            bot.myBrowser = Mock(current_url=ARTICLE)
            liked, collection, close = Mock(), Mock(), Mock()
            def locate(xpath, timeout=15):
                if 'isactive' in xpath:
                    return liked
                if "@class='is-collection'" in xpath:
                    return collection
                if 'csdn-collection-close' in xpath:
                    return close
                return None
            bot.find_ele = Mock(side_effect=locate)
            self.assertFalse(bot.csdn_dian_ping())
            liked.click.assert_not_called()
            collection.click.assert_called_once()
            close.click.assert_called_once()

    def test_message_timeout_is_not_resent(self):
        for module in MODULES:
            with tempfile.TemporaryDirectory() as directory:
                bot = module.CSDN(data_dir=directory)
                bot.state_path = Path(directory) / 'state.json'
                bot.myBrowser = Mock()
                editor = Mock()
                editor.get_attribute.return_value = ''
                bot.find_ele = Mock(return_value=editor)
                with patch.object(module, 'WebDriverWait') as wait:
                    wait.return_value.until.side_effect = module.TimeoutException()
                    self.assertFalse(bot.send_chat_message('test', 'key'))
                self.assertEqual(bot.state['messages']['key'], 'pending')
                self.assertFalse(bot.send_chat_message('test', 'key'))
                self.assertEqual(editor.send_keys.call_count, 2)
                self.assertIn('delete window.__csdnBotSendObserver', bot.myBrowser.execute_script.call_args.args[0])

    def test_message_acknowledgement_is_persisted(self):
        for module in MODULES:
            with tempfile.TemporaryDirectory() as directory:
                bot = module.CSDN(data_dir=directory)
                bot.state_path = Path(directory) / 'state.json'
                bot.myBrowser = Mock()
                bot.myBrowser.execute_script.return_value = True
                editor = Mock()
                editor.get_attribute.return_value = ''
                bot.find_ele = Mock(return_value=editor)
                self.assertTrue(bot.send_chat_message('test', 'key'))
                self.assertEqual(json.loads(bot.state_path.read_text())['messages']['key'], 'confirmed')

    def test_article_tab_cleanup(self):
        for module in MODULES:
            bot = module.CSDN()
            driver = Mock(current_window_handle='origin')
            driver.window_handles = ['origin', 'unrelated']
            def new_window(kind):
                driver.window_handles.append('article')
                driver.current_window_handle = 'article'
            driver.switch_to.new_window.side_effect = new_window
            driver.switch_to.window.side_effect = lambda handle: setattr(driver, 'current_window_handle', handle)
            driver.close.side_effect = lambda: driver.window_handles.remove(driver.current_window_handle)
            bot.myBrowser = driver
            bot.csdn_dian_ping = Mock(side_effect=RuntimeError('failed'))
            with self.assertRaises(RuntimeError):
                bot.visit_article(ARTICLE, 'test')
            self.assertEqual(driver.window_handles, ['origin', 'unrelated'])
            self.assertEqual(driver.current_window_handle, 'origin')

    def test_run_cleanup_on_startup_failure(self):
        for module in MODULES:
            bot = module.CSDN()
            bot.myBrowser = Mock()
            bot.start_browser = Mock(side_effect=RuntimeError('login failed'))
            with self.assertRaises(RuntimeError):
                bot.run()
            bot.myBrowser.quit.assert_called_once()

    def test_run_backoff_and_interrupt(self):
        for module in MODULES:
            bot = module.CSDN()
            bot.myBrowser = Mock()
            bot.start_browser = Mock()
            bot.csdn_hu_boke = Mock(side_effect=RuntimeError('failure'))
            with patch.object(module.time, 'sleep', side_effect=KeyboardInterrupt) as sleep:
                bot.run()
            sleep.assert_called_once_with(5)
            bot.myBrowser.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
