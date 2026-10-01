import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from selenium.webdriver.common.by import By

from application_limits import (
    DAILY_LIMIT_EXIT_CODE,
    DailyApplyLimitReached,
)
from linkedineasyapply import LinkedinEasyApply
from main import run_bot
from scheduler_gui import SchedulerGUI, ScheduleType, TaskStatus, UserTask


class DailyLimitDetectionTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        self.bot.browser = Mock()
        self.bot.browser.find_elements.return_value = [Mock(text="")]
        self.bot._shadow_elements = Mock(return_value=[])

    def test_limit_text_variants_stop_before_any_job_click(self):
        for text in (
            "You reached today's Easy Apply limit",
            "You've reached today’s Easy Apply limit",
            "You've reached the Easy Apply application limit for today.",
            "您已达到今天的快速申请限额",
        ):
            with self.subTest(text=text):
                self.bot.browser.find_elements.return_value = [Mock(text=text)]
                with self.assertRaises(DailyApplyLimitReached):
                    self.bot.apply_to_job()
        self.bot.browser.execute_script.assert_not_called()

    def test_shadow_limit_stops_while_waiting_for_form(self):
        self.bot._shadow_elements.return_value = [
            Mock(text="You reached today's Easy Apply limit")
        ]
        self.bot._continue_easy_apply_warning = Mock()
        with self.assertRaises(DailyApplyLimitReached):
            self.bot._find_easy_apply_context()
        self.bot._continue_easy_apply_warning.assert_not_called()

    def test_clicking_easy_apply_then_showing_limit_stops_without_filling(self):
        body = Mock(text="")
        apply_button = Mock()
        apply_button.get_attribute.side_effect = lambda name: (
            "jobs-apply-button" if name == "class" else "Easy Apply to Test"
        )
        apply_button.click.side_effect = lambda: setattr(
            body, "text", "You reached today's Easy Apply limit"
        )
        self.bot.browser.find_elements.side_effect = lambda by, selector: (
            [body] if by == By.TAG_NAME and selector == "body" else [apply_button]
        )
        self.bot.fill_up = Mock()
        with self.assertRaises(DailyApplyLimitReached):
            self.bot.apply_to_job()
        apply_button.click.assert_called_once()
        self.bot.fill_up.assert_not_called()

    def test_delayed_limit_popup_is_detected_during_form_wait(self):
        self.bot.browser.find_elements.side_effect = [
            [Mock(text="")], [Mock(text="You reached today's Easy Apply limit")]
        ]
        self.bot._visible_elements = Mock(return_value=[])
        self.bot._continue_easy_apply_warning = Mock(return_value=False)
        with patch("linkedineasyapply.time.sleep"):
            with self.assertRaises(DailyApplyLimitReached):
                self.bot._find_easy_apply_context()

    def test_hidden_old_markup_and_job_fit_warning_do_not_stop(self):
        self.bot.browser.page_source = "You reached today's Easy Apply limit"
        self.bot.browser.find_elements.return_value = [
            Mock(text="This job may not be the best fit. Continue applying")
        ]
        self.bot._raise_if_daily_apply_limit()

    def test_existing_form_is_still_found_without_limit(self):
        form = Mock()
        self.bot._visible_elements = Mock(return_value=[form])
        self.assertIs(self.bot._find_easy_apply_context(), form)

    def test_limit_after_submit_is_not_converted_to_generic_failure(self):
        apply_button = Mock()
        apply_button.get_attribute.side_effect = lambda name: (
            "jobs-apply-button" if name == "class" else "Easy Apply to Test"
        )
        self.bot.browser.find_elements.return_value = [apply_button]
        self.bot._find_easy_apply_context = Mock(return_value=Mock())
        self.bot._raise_if_daily_apply_limit = Mock(side_effect=[
            None, None, None, None, None, DailyApplyLimitReached(),
        ])
        self.bot.fill_up = Mock(return_value=True)
        submit = Mock(text="Submit application")
        self.bot._find_easy_apply_primary_button = Mock(return_value=submit)
        self.bot.unfollow = Mock()
        self.bot._dismiss_easy_apply = Mock()
        self.bot.FastMode = False
        with patch("linkedineasyapply.time.sleep"):
            with self.assertRaises(DailyApplyLimitReached):
                self.bot.apply_to_job()
        submit.click.assert_called_once()
        self.bot._dismiss_easy_apply.assert_not_called()

    def test_limit_propagates_out_of_search_in_both_position_modes(self):
        for position_configs in ([], [{"name": "Engineer", "count": 10}]):
            with self.subTest(position_configs=position_configs):
                self.bot.positions_with_count = position_configs
                self.bot.positions = ["Engineer", "Designer"]
                self.bot.locations = ["United States"]
                self.bot.applied_counts = {}
                self.bot.start_from_page = 1
                self.bot.FastMode = False
                self.bot.click_location_url = Mock(return_value="1")
                self.bot.next_job_page = Mock()
                self.bot.apply_jobs = Mock(side_effect=DailyApplyLimitReached())
                with patch("linkedineasyapply.time.sleep"):
                    with self.assertRaises(DailyApplyLimitReached):
                        self.bot.start_applying()
                self.bot.apply_jobs.assert_called_once()
                self.bot.next_job_page.assert_called_once()


class DailyLimitStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = Path(self.temp_dir.name) / "account.yaml"
        self.config.write_text("email: test@example.com\n", encoding="utf-8")
        self.gui = SchedulerGUI.__new__(SchedulerGUI)
        self.gui.schedule_type = ScheduleType.INTERVAL
        self.gui.schedule_interval = 2
        self.gui.running = True
        self.gui.log = Mock()
        self.gui.update_tasks_display = Mock()

    def test_cli_limit_ends_only_current_run_and_allows_retry(self):
        browser = Mock()
        bot = Mock()
        bot.start_applying.side_effect = DailyApplyLimitReached()
        with patch("main.validate_yaml", return_value={}), \
                patch("main.init_browser", return_value=browser), \
                patch("main.LinkedinEasyApply", return_value=bot):
            self.assertEqual(run_bot(str(self.config)), DAILY_LIMIT_EXIT_CODE)
            bot.start_applying.side_effect = None
            self.assertEqual(run_bot(str(self.config)), 0)
        browser.quit.assert_called_once()
        self.assertEqual(bot.start_applying.call_count, 2)
        self.assertEqual(self.config.read_text(), "email: test@example.com\n")

    def test_manual_queue_accepts_account_with_previous_limit(self):
        task = UserTask("account", str(self.config))
        task.status = TaskStatus.DAILY_LIMIT
        self.gui.user_tasks = {"account": task}
        self.gui.task_queue = Mock()
        self.gui.update_queue_display = Mock()
        self.gui.texts = {"added_to_queue": "Added", "tasks_to_queue": "tasks"}
        self.gui.queue_selected_tasks()
        self.gui.task_queue.put.assert_called_once_with(task)
        self.assertEqual(task.status, TaskStatus.QUEUED)

    def test_next_run_uses_configured_interval_and_keeps_limit_status(self):
        task = UserTask("account", str(self.config))
        task.status = TaskStatus.DAILY_LIMIT
        before = datetime.now()
        self.gui.calculate_next_run_time_for_task(task)
        self.assertGreaterEqual(task.next_run, before + timedelta(minutes=2))
        self.assertLess(task.next_run, before + timedelta(minutes=3))
        self.assertEqual(task.status, TaskStatus.DAILY_LIMIT)

    def test_manual_mode_does_not_invent_retry_time(self):
        task = UserTask("account", str(self.config))
        task.status = TaskStatus.DAILY_LIMIT
        self.gui.schedule_type = ScheduleType.MANUAL
        self.gui.calculate_next_run_time_for_task(task)
        self.assertEqual(task.status, TaskStatus.DAILY_LIMIT)
        self.assertIsNone(task.next_run)

    def test_automatic_schedule_can_queue_previous_limit_result(self):
        task = UserTask("account", str(self.config))
        task.status = TaskStatus.DAILY_LIMIT
        task.next_run = datetime.now() - timedelta(seconds=1)
        self.gui.user_tasks = {"account": task}
        self.gui.task_queue = Mock()
        self.gui.update_queue_display = Mock()
        self.gui.interruptible_sleep = lambda _: setattr(self.gui, "running", False)
        self.gui.scheduler_loop()
        self.gui.task_queue.put.assert_called_once_with(task)
        self.assertEqual(task.status, TaskStatus.QUEUED)

    def test_special_exit_code_is_not_marked_success_or_regular_failure(self):
        task = UserTask("account", str(self.config))
        process = Mock()
        process.poll.return_value = DAILY_LIMIT_EXIT_CODE
        self.gui.MAIN_SCRIPT = "main.py"
        with patch("scheduler_gui.subprocess.Popen", return_value=process), \
                patch("scheduler_gui.threading.Thread"):
            self.gui.run_single_task(task)
        self.assertEqual(task.status, TaskStatus.DAILY_LIMIT)
        self.assertGreater(task.next_run, datetime.now())
        self.assertLess(task.next_run, datetime.now() + timedelta(minutes=3))
        # A later run can succeed; the previous limit is only a result status.
        process.poll.return_value = 0
        with patch("scheduler_gui.subprocess.Popen", return_value=process) as spawn, \
                patch("scheduler_gui.threading.Thread"):
            self.gui.run_single_task(task)
        spawn.assert_called_once()
        self.assertEqual(task.status, TaskStatus.SUCCESS)

    def test_old_cooldown_files_do_not_block_cli_or_scheduler(self):
        for content in ('{"retry_after": 9999999999}', '{broken'):
            with self.subTest(content=content):
                self.config.with_suffix(".daily-limit.json").write_text(content)
                task = UserTask("account", str(self.config))
                self.assertEqual(task.status, TaskStatus.IDLE)
                browser = Mock()
                with patch("main.validate_yaml", return_value={}), \
                        patch("main.init_browser", return_value=browser) as initialize, \
                        patch("main.LinkedinEasyApply", return_value=Mock()):
                    self.assertEqual(run_bot(str(self.config)), 0)
                initialize.assert_called_once()


if __name__ == "__main__":
    unittest.main()
