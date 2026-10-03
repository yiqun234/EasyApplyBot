import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import StaleElementReferenceException, WebDriverException

from linkedineasyapply import ApplicationSubmissionUnconfirmed, LinkedinEasyApply


class ApplicationProgressTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        self.bot.browser = Mock()
        apply_button = Mock()
        apply_button.get_attribute.return_value = 'jobs-apply-button'
        self.bot.browser.find_elements.return_value = [apply_button]
        self.context = Mock()
        self.bot._find_easy_apply_context = Mock(return_value=self.context)
        self.bot._raise_if_daily_apply_limit = Mock()
        self.bot.fill_up = Mock(return_value=True)
        self.button = Mock(text='Review')
        self.bot._find_easy_apply_primary_button = Mock(return_value=self.button)
        self.bot._application_form_state = Mock(return_value={'signature': 'step-1', 'errors': []})
        self.bot._application_confirmation_visible = Mock(return_value=False)
        self.bot._dismiss_easy_apply = Mock(return_value=True)
        self.bot.unfollow = Mock()
        self.bot.FastMode = False
        wait = self.bot._wait_for_application_progress
        self.bot._wait_for_application_progress = lambda *args, **kwargs: wait(*args, timeout=0.005, **kwargs)
        self.sleep = patch('linkedineasyapply.time.sleep').start()
        self.addCleanup(patch.stopall)

    def test_unchanged_review_stops_after_one_click(self):
        with self.assertRaisesRegex(RuntimeError, 'did not advance after review'):
            self.bot.apply_to_job()
        self.button.click.assert_called_once()
        self.bot.fill_up.assert_called_once()

    def test_validation_error_names_field_instead_of_repeating_review(self):
        self.bot._application_form_state.side_effect = [
            {'signature': 'step-1', 'errors': []},
            {'signature': 'step-1', 'errors': ['Resume: file required']},
        ]
        with self.assertRaisesRegex(RuntimeError, 'Resume: file required'):
            self.bot.apply_to_job()
        self.button.click.assert_called_once()

    def test_next_can_advance_to_another_next_page(self):
        self.bot._application_form_state.return_value = {'signature': 'step-2', 'errors': []}
        result = self.bot._wait_for_application_progress(
            self.context, {'signature': 'step-1'}, 'next'
        )
        self.assertIs(result, self.context)

    def test_new_page_can_have_required_fields_not_filled_yet(self):
        self.bot._application_form_state.return_value = {
            'signature': 'step-2', 'errors': ['Phone: Please fill out this field.'],
        }
        self.assertIs(self.bot._wait_for_application_progress(
            self.context, {'signature': 'step-1'}, 'next'
        ), self.context)

    def test_confirmed_submission_succeeds_even_if_dialog_cleanup_fails(self):
        self.button.text = 'Submit application'
        self.bot._application_confirmation_visible.return_value = True
        self.bot._dismiss_easy_apply.side_effect = StaleElementReferenceException()
        self.assertTrue(self.bot.apply_to_job())
        self.button.click.assert_called_once()

    def test_missing_receipt_is_unknown_and_never_resubmitted(self):
        self.button.text = 'Submit application'
        with self.assertRaises(ApplicationSubmissionUnconfirmed):
            self.bot.apply_to_job()
        self.button.click.assert_called_once()
        self.bot._dismiss_easy_apply.assert_called_once_with(self.context, discard=False)

    def test_submit_transport_error_is_unknown(self):
        self.button.text = 'Submit application'
        self.button.click.side_effect = TimeoutError('network')
        with self.assertRaises(ApplicationSubmissionUnconfirmed):
            self.bot.apply_to_job()
        self.button.click.assert_called_once()

    def test_browser_failure_after_submit_is_not_a_confirmed_failure(self):
        self.button.text = 'Submit application'
        self.bot._application_confirmation_visible.side_effect = WebDriverException('disconnected')
        with self.assertRaises(ApplicationSubmissionUnconfirmed):
            self.bot.apply_to_job()
        self.button.click.assert_called_once()

    def test_new_dialog_is_reacquired_after_rerender(self):
        replacement = Mock()
        self.bot._find_easy_apply_context.return_value = replacement
        self.bot._application_form_state.side_effect = [
            StaleElementReferenceException(), {'signature': 'step-2', 'errors': []},
        ]
        self.assertIs(self.bot._wait_for_application_progress(
            self.context, {'signature': 'step-1'}, 'review'
        ), replacement)


class ApplicationReceiptTests(unittest.TestCase):
    def test_only_explicit_receipts_are_accepted(self):
        bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        bot.browser = Mock()
        bot._shadow_elements = Mock(return_value=[])
        for text, expected in (
            ('Your application was sent to Example Company\nDone', True),
            ('Application submitted', True),
            ('Application sent\nTrack your application', True),
            ('Review your application\nSubmit application', False),
            ('Application sent.pdf', False),
            ('Your application will be submitted', False),
        ):
            with self.subTest(text=text):
                bot._visible_elements = Mock(return_value=[Mock(text=text)])
                self.assertEqual(bot._application_confirmation_visible(), expected)


if __name__ == '__main__':
    unittest.main()
