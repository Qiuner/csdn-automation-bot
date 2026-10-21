import os
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

from test_browser_helpers import MODULES
from test_comment_revisit import CommentRevisit
from visit_probe import VisitProbe


class DomElement:
    def __init__(self, locator):
        self.locator = locator

    def is_displayed(self):
        return self.locator.is_visible()

    def get_attribute(self, name):
        return self.locator.get_attribute(name)

    def click(self):
        self.locator.click()


@unittest.skipUnless(os.environ.get('CSDN_DOM_BROWSER_TESTS') == '1', '可选本地浏览器 DOM 测试')
class PageCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)

    def bot(self, module):
        bot = module.CSDN()
        bot.myBrowser = Mock(current_url='https://blog.csdn.net/test/article/details/123')
        bot.myBrowser.find_elements.side_effect = lambda by, selector: [
            DomElement(locator) for locator in self.page.locator(('xpath=' if by == 'xpath' else '') + selector).all()]
        find = bot.find_ele
        bot.find_ele = lambda xpath, timeout=15: find(xpath, timeout=min(timeout, 0.05))
        return bot

    def test_new_sidebar_respects_active_state_and_confirms_new_actions(self):
        for module in MODULES:
            for active in (False, True):
                with self.subTest(module=module.__name__, active=active):
                    self.page.set_content(''.join(
                        f'<div id="sidebar-{action}" class="sidebar-item {"active" if active else ""}" '
                        'onclick="this.classList.add(\'active\'); this.dataset.clicked=\'yes\'">action</div>'
                        for action in ('like', 'collect')))
                    bot = self.bot(module)
                    bot.state['articles'][bot.myBrowser.current_url] = {'comment': 'confirmed'}
                    self.assertTrue(bot.csdn_dian_ping())
                    for action in ('like', 'collect'):
                        self.assertEqual(self.page.locator('#sidebar-' + action).get_attribute('data-clicked'),
                                         None if active else 'yes')

    def test_new_comment_entry_reveals_reward_without_claiming(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                self.page.set_content('''
                    <a class="sidebar-item go-side-comment" onclick="document.querySelector('#pcCommentSideBox').style.display='block'">comments</a>
                    <div id="pcCommentSideBox" style="display:none">
                      <div class="comment-reward-item" data-status="available" onclick="document.body.dataset.claimed='yes'">reward</div>
                    </div>''')
                bot = self.bot(module)
                self.assertFalse(bot.csdn_hong_bao(dry_run=True))
                self.assertTrue(self.page.locator('#pcCommentSideBox').is_visible())
                self.assertIsNone(self.page.locator('body').get_attribute('data-claimed'))

    def test_revisit_recognizes_new_original_metadata(self):
        bot = self.bot(SimpleNamespace(CSDN=CommentRevisit))
        target = bot.myBrowser.current_url
        def navigate(url):
            bot.myBrowser.current_url = url
            self.page.set_content(
                f'<div class="blog-list-box"><a href="{target}">Article</a></div>'
                if '?type=lately' in url else
                '<div class="simple-meta-row"><span class="simple-meta-entry simple-meta-text">原创</span></div>')
        bot.myBrowser.get.side_effect = navigate
        bot.myBrowser.execute_script.side_effect = lambda script: self.page.evaluate('() => {' + script + '}')
        result = bot.latest_article({'profile': 'https://blog.csdn.net/test', 'username': 'test'}, max_articles=1)
        self.assertEqual(result, {'url': target, 'title': 'Article'})

    def test_community_sidebar_reveals_expired_card_without_claim(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                self.page.set_content('''
                    <div class="detail-shell-toolbar__item is-comment" onclick="document.querySelector('aside').style.display='block'">comments</div>
                    <aside class="detail-comment-side" style="display:none">
                      <div class="redpack-card redpack-card-overdue" onclick="document.body.dataset.claimed='yes'">expired</div>
                    </aside>''')
                bot = self.bot(module)
                self.assertFalse(bot.csdn_hong_bao(dry_run=True))
                self.assertTrue(self.page.locator('aside').is_visible())
                self.assertIsNone(self.page.locator('body').get_attribute('data-claimed'))

    def test_visit_counter_reads_only_metadata_and_preserves_precision(self):
        bot = self.bot(SimpleNamespace(CSDN=VisitProbe))
        bot.myBrowser.execute_script.side_effect = lambda script: self.page.evaluate('() => {' + script + '}')
        for markup, expected in (
            ('<span class="simple-meta-entry" title="阅读量：1705">1.7k阅读</span>', 1705),
            ('<span class="simple-meta-entry">1.7k阅读</span>', None),
            ('<span class="simple-meta-entry">阅读 0</span>', 0),
        ):
            with self.subTest(markup=markup):
                self.page.set_content('<div class="simple-meta-row">'
                                      '<span class="simple-meta-entry">2026-10-20 12:00</span>'
                                      '<span class="simple-meta-entry">原创</span>' + markup + '</div>'
                                      '<article>阅读量：999999</article>')
                self.assertEqual(bot.read_counter()['count'], expected)


if __name__ == '__main__':
    unittest.main()
