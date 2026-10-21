import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
import visit_schedule
from visit_probe import VisitProbe


class ScheduleTests(unittest.TestCase):
    def test_random_wait_and_original_deadline(self):
        bot = VisitProbe()
        bot.start_browser = Mock()
        bot.myBrowser = Mock()
        bot.myBrowser.get_cookie.return_value = {'value': 'owner'}
        bot.sample = Mock(return_value={'count': 100, 'display': '100'})
        clock = [0]
        started = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(visit_schedule, 'datetime') as dates, \
                patch.object(visit_schedule.time, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(visit_schedule.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)) as sleep, \
                patch.object(visit_schedule.random, 'randint', side_effect=[50, 70]) as randint:
            dates.now.return_value = started
            report = visit_schedule.run_schedule(bot, 'https://blog.csdn.net/owner/article/details/123',
                60, 24, Path(folder) / 'report.json', jitter=10, until=started + timedelta(seconds=110))
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [50, 60])
            self.assertEqual(clock[0], 110)
            self.assertEqual(bot.sample.call_count, 2)
            self.assertEqual(report['status'], 'completed')
            self.assertEqual(report['ends_at'], (started + timedelta(seconds=110)).isoformat())
            randint.assert_called_with(50, 70)

    def test_fixed_slots_deadline_and_delta(self):
        bot = VisitProbe()
        bot.start_browser = Mock()
        bot.myBrowser = Mock()
        bot.myBrowser.get_cookie.return_value = {'value': 'owner'}
        clock = [0]

        def sample(*args):
            clock[0] += 20
            return {'count': int(clock[0]), 'display': str(clock[0])}

        bot.sample = Mock(side_effect=sample)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            with patch.object(visit_schedule.time, 'monotonic', side_effect=lambda: clock[0]), \
                    patch.object(visit_schedule.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
                report = visit_schedule.run_schedule(bot, 'https://blog.csdn.net/owner/article/details/123', 180, 1, output)
            self.assertEqual(clock[0], 3600)
            self.assertEqual(bot.sample.call_count, 20)
            self.assertEqual(report['samples'][1]['count'], 200)
            self.assertEqual(report['observed_delta'], 3420)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'completed')
            bot.myBrowser.quit.assert_called_once()

    def test_failure_retained_and_no_retry(self):
        bot = VisitProbe()
        bot.start_browser = Mock(side_effect=RuntimeError('expired'))
        bot.myBrowser = Mock()
        bot.sample = Mock()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            with self.assertRaises(RuntimeError):
                visit_schedule.run_schedule(bot, 'https://blog.csdn.net/owner/article/details/123', 180, 1, output)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'failed')
            bot.sample.assert_not_called()
            bot.myBrowser.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
