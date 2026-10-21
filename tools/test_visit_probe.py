import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
import visit_probe
from visit_probe import VisitProbe, parse_counter

ARTICLE = 'https://blog.csdn.net/owner/article/details/123'


class VisitProbeTests(unittest.TestCase):
    def test_counter_keeps_rounded_values_unknown(self):
        for text, count in [('1,234阅读', 1234), ('阅读量：1234', 1234), ('0', 0),
                            ('1.7k阅读', None), ('2万', None), ('100+', None)]:
            with self.subTest(text=text):
                self.assertEqual(parse_counter(text)['count'], count)
        for text in ('原创', '2026-10-20', '1,2', '评论 23', ''):
            self.assertIsNone(parse_counter(text))

    def test_sample_checks_owner_and_redirect_before_counter(self):
        for owner, current in [('owner', ARTICLE), ('other', ARTICLE),
                               ('owner', ARTICLE + '4')]:
            with self.subTest(owner=owner, current=current):
                bot = VisitProbe()
                bot.myBrowser = Mock(current_url=current)
                bot.myBrowser.get_cookie.return_value = {'value': 'owner'}
                canonical = Mock()
                canonical.get_attribute.return_value = ARTICLE.replace('/owner/', '/' + owner + '/')
                bot.myBrowser.find_elements.return_value = [canonical]
                bot.myBrowser.execute_script.return_value = [{'text': '1.7k阅读', 'title': '阅读量：1701'}]
                if owner == 'owner' and current == ARTICLE:
                    self.assertEqual(bot.sample(ARTICLE, 'owner')['count'], 1701)
                else:
                    with self.assertRaises(RuntimeError):
                        bot.sample(ARTICLE, 'owner')
                    bot.myBrowser.execute_script.assert_not_called()
                bot.myBrowser.get.assert_called_once_with(ARTICLE)

    def test_probe_is_bounded_and_reports_only_observed_delta(self):
        with tempfile.TemporaryDirectory() as directory:
            bot = VisitProbe()
            bot.myBrowser = Mock()
            bot.myBrowser.get_cookie.return_value = {'value': 'owner'}
            bot.sample = Mock(side_effect=[{'display': '100', 'count': 100},
                                          {'display': '102', 'count': 102}])
            output = Path(directory) / 'report.json'
            with patch.object(visit_probe.time, 'sleep') as sleep:
                report = bot.probe(ARTICLE, 2, 60, output)
            self.assertEqual(bot.sample.call_count, 2)
            sleep.assert_called_once_with(60)
            self.assertEqual(report['observed_delta'], 2)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'completed')
            with self.assertRaises(FileExistsError):
                bot.probe(ARTICLE, 2, 60, output)
            self.assertEqual(bot.sample.call_count, 2)

    def test_probe_stops_on_failure_and_retains_prior_sample(self):
        for failure, status in ((RuntimeError('owner changed'), 'failed'), (KeyboardInterrupt(), 'interrupted')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                bot = VisitProbe()
                bot.myBrowser = Mock()
                bot.myBrowser.get_cookie.return_value = {'value': 'owner'}
                bot.sample = Mock(side_effect=[{'display': '1.7k', 'count': None}, failure])
                output = Path(directory) / 'report.json'
                with patch.object(visit_probe.time, 'sleep'), self.assertRaises(type(failure)):
                    bot.probe(ARTICLE, 3, 60, output)
                report = json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(report['status'], status)
                self.assertEqual(len(report['samples']), 1)
                self.assertIsNone(report['observed_delta'])
                self.assertEqual(bot.sample.call_count, 2)

    def test_preview_never_starts_browser(self):
        with patch.object(sys, 'argv', ['visit_probe.py', ARTICLE]), patch.object(VisitProbe, 'start_browser') as start:
            visit_probe.main()
        start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
