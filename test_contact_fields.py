import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from linkedineasyapply import LinkedinEasyApply


class Field:
    def __init__(self, tag='input', text='', selected=False, **attributes):
        self.tag_name = tag
        self.text = text
        self.attributes = attributes
        self.selected = selected
        self.is_displayed = Mock(return_value=True)
        self.is_enabled = Mock(return_value=True)
        self.clear = Mock(side_effect=lambda: self.attributes.update(value=''))
        self.click = Mock()
        self.select_all = False
        self.send_keys = Mock(side_effect=self.type_keys)

    def type_keys(self, *keys):
        if keys in ((Keys.CONTROL, 'a'), (Keys.COMMAND, 'a')):
            self.select_all = True
        elif keys == (Keys.BACKSPACE,):
            current = self.attributes.get('value', '')
            self.attributes['value'] = '' if self.select_all else current[:-1]
            self.select_all = False
        else:
            current = '' if self.select_all else self.attributes.get('value', '')
            self.attributes['value'] = current + ''.join(str(key) for key in keys)
            self.select_all = False

    def get_attribute(self, name):
        return self.attributes.get(name, '')

    def is_selected(self):
        return self.selected


class NativeSelect:
    def __init__(self, options):
        self.options = options
        self.select_by_visible_text = Mock(side_effect=self.choose)

    @property
    def first_selected_option(self):
        return next(option for option in self.options if option.selected)

    def choose(self, text):
        for option in self.options:
            option.selected = option.text == text


class Form:
    def __init__(self, fields, labels=(), heading=None, questions=()):
        self.fields = fields
        self.labels = labels
        self.heading = heading
        self.questions = questions

    def find_elements(self, by, value):
        if by == By.CSS_SELECTOR and value == 'input, select':
            return self.fields
        if by == By.TAG_NAME and value == 'label':
            return self.labels
        if by == By.TAG_NAME and value == 'h3':
            return [Field('h3', text=self.heading)] if self.heading else []
        if by == By.CLASS_NAME and value == 'fb-dash-form-element':
            return self.questions
        return []

    def find_element(self, by, value):
        if by == By.TAG_NAME and value == 'form':
            return self
        raise NoSuchElementException()


class ContactFieldTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        self.bot.personal_info = {
            'Mobile Phone Number': '4155550123',
            'Phone Country Code': 'United States (+1)',
            'City': 'San Francisco',
        }
        self.bot.email = 'test@example.com'
        self.bot.send_resume = Mock()
        self.bot.ai_response_generator = Mock()
        self.bot.record_unprepared_question = Mock()

    def test_spanish_contact_step_replaces_ai_sentence_with_configured_phone(self):
        phone = Field(id='phoneNumber-nationalNumber', type='text',
                      value='No tengo un número de teléfono móvil proporcionado.')
        form = Form([phone], [Field('label', text='Teléfono móvil*', **{'for': phone.get_attribute('id')})],
                    heading='Información de contacto')
        context = Mock()
        context.find_element.return_value = form
        self.assertTrue(self.bot.fill_up(context))
        phone.send_keys.assert_called_with('4155550123')
        self.assertEqual(phone.get_attribute('value'), '4155550123')
        self.bot.ai_response_generator.generate_response.assert_not_called()

    def test_english_contact_step_remains_supported(self):
        phone = Field(id='phoneNumber-nationalNumber', type='text')
        form = Form([phone], heading='Contact info')
        context = Mock()
        context.find_element.return_value = form
        self.assertTrue(self.bot.fill_up(context))
        phone.send_keys.assert_called_once_with('4155550123')

    def test_missing_heading_still_fills_structural_phone_field(self):
        phone = Field(type='tel', id='opaque-field')
        context = Mock()
        context.find_element.return_value = Form([phone])
        self.assertTrue(self.bot.fill_up(context))
        phone.send_keys.assert_called_once_with('4155550123')

    def test_spanish_label_identifies_opaque_text_input(self):
        field = Field(type='text', id='opaque-field')
        self.assertTrue(self.bot._fill_contact_field(Form([field]), field, 'Teléfono móvil*'))
        field.send_keys.assert_called_once_with('4155550123')

    def test_non_english_phone_autocomplete_is_recognized(self):
        field = Field(type='text', autocomplete='section-contact tel-national')
        self.assertTrue(self.bot._fill_contact_field(Form([field]), field, '未知语言'))
        field.send_keys.assert_called_once_with('4155550123')

    def test_additional_questions_fills_all_contact_fields_before_ai(self):
        country = Field('select', id='phoneNumber-country')
        phone = Field(type='tel', id='phoneNumber-nationalNumber')
        email = Field(type='email', id='email-address')
        question = Form([country, phone, email])
        form = Form([], questions=[question])
        choices = NativeSelect([
            Field('option', text='Canadá (+1)', value='CA', selected=True),
            Field('option', text='Estados Unidos (+1)', value='US'),
        ])
        self.bot._extract_question_text = Mock(return_value='Código del país Teléfono móvil Email')
        with patch('linkedineasyapply.Select', return_value=choices):
            self.bot.additional_questions(form)
        choices.select_by_visible_text.assert_called_once_with('Estados Unidos (+1)')
        phone.send_keys.assert_called_once_with('4155550123')
        email.send_keys.assert_called_once_with('test@example.com')
        self.bot.ai_response_generator.generate_response.assert_not_called()
        self.bot.record_unprepared_question.assert_not_called()

    def test_missing_or_invalid_phone_never_falls_through_to_ai(self):
        for number in ('', None, '123', 'No phone provided', True):
            with self.subTest(number=number):
                self.bot.personal_info['Mobile Phone Number'] = number
                phone = Field(type='tel')
                question = Form([phone])
                self.bot._extract_question_text = Mock(return_value='Teléfono móvil')
                self.bot.additional_questions(Form([], questions=[question]))
                phone.send_keys.assert_not_called()
        self.bot.ai_response_generator.generate_response.assert_not_called()

    def test_matching_existing_phone_is_not_reentered(self):
        phone = Field(type='tel', value='4155550123')
        self.assertTrue(self.bot._fill_contact_field(Form([phone]), phone))
        phone.clear.assert_not_called()
        phone.send_keys.assert_not_called()

    def test_formatted_international_phone_is_preserved(self):
        self.bot.personal_info['Mobile Phone Number'] = '+1 (415) 555-0123'
        phone = Field(type='tel')
        self.bot._fill_contact_field(Form([phone]), phone)
        phone.send_keys.assert_called_once_with('+1 (415) 555-0123')

    def test_english_phone_country_option_matches_directly(self):
        field = Field('select', id='phoneNumber-country')
        choices = NativeSelect([
            Field('option', text='China (+86)', value='CN', selected=True),
            Field('option', text='United States (+1)', value='US'),
        ])
        with patch('linkedineasyapply.Select', return_value=choices):
            self.assertTrue(self.bot._select_phone_country(field, 'United States (+1)'))
        choices.select_by_visible_text.assert_called_once_with('United States (+1)')

    def test_shared_dialing_code_without_region_is_not_guessed(self):
        field = Field('select')
        choices = NativeSelect([
            Field('option', text='Canadá (+1)', value='CA', selected=True),
            Field('option', text='Estados Unidos (+1)', value='US'),
        ])
        with patch('linkedineasyapply.Select', return_value=choices):
            self.assertFalse(self.bot._select_phone_country(field, '+1'))
        choices.select_by_visible_text.assert_not_called()

    def test_known_region_is_not_replaced_with_another_country_sharing_code(self):
        field = Field('select')
        choices = NativeSelect([Field('option', text='Canadá (+1)', value='CA', selected=True)])
        with patch('linkedineasyapply.Select', return_value=choices):
            self.assertFalse(self.bot._select_phone_country(field, 'United States (+1)'))
        choices.select_by_visible_text.assert_not_called()

    def test_unique_dialing_code_matches_localized_country(self):
        field = Field('select')
        choices = NativeSelect([
            Field('option', text='España (+34)', value='ES', selected=True),
            Field('option', text='भारत (+91)', value='IN'),
        ])
        with patch('linkedineasyapply.Select', return_value=choices):
            self.assertTrue(self.bot._select_phone_country(field, 'India (+91)'))
        choices.select_by_visible_text.assert_called_once_with('भारत (+91)')

    def test_country_selection_error_does_not_enter_ai_branch(self):
        field = Field('select', id='phoneNumber-country')
        self.bot._select_phone_country = Mock(side_effect=StaleElementReferenceException())
        self.bot._extract_question_text = Mock(return_value='Código del país')
        self.bot.additional_questions(Form([], questions=[Form([field])]))
        self.bot.ai_response_generator.generate_response.assert_not_called()

    def test_email_dropdown_selects_configured_email_without_ai(self):
        field = Field('select', id='emailAddress')
        choices = NativeSelect([
            Field('option', text='Seleccione una opción', value='', selected=True),
            Field('option', text='test@example.com', value='test@example.com'),
        ])
        with patch('linkedineasyapply.Select', return_value=choices):
            self.bot._fill_contact_field(Form([field]), field, 'Correo electrónico')
        choices.select_by_visible_text.assert_called_once_with('test@example.com')

    def test_city_still_uses_typeahead_selection(self):
        city = Field(type='text', id='GEO-LOCATION')
        form = Form([city])
        self.bot._select_typeahead_option = Mock(return_value=True)
        self.bot._fill_contact_field(form, city, 'Ciudad')
        self.bot._select_typeahead_option.assert_called_once_with(form, city, 'San Francisco')

    def test_non_contact_fields_are_not_claimed(self):
        cases = (
            (Field(type='text'), 'Describe your experience with telephone sales'),
            (Field('select', id='country'), 'Country of residence'),
            (Field(type='radio'), 'Phone number'),
            (Field(type='hidden', id='phoneNumber-nationalNumber'), ''),
        )
        for field, label in cases:
            with self.subTest(label=label):
                self.assertFalse(self.bot._fill_contact_field(Form([field]), field, label))


class TextReplacementTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        self.bot.browser = Mock(capabilities={'platformName': 'windows'})

    def field(self, value, tag='input'):
        field = Field(tag, type='text', value=value)
        # A controlled input can restore its old state after WebDriver.clear().
        field.clear.side_effect = None
        return field

    def test_correct_prefilled_name_is_untouched(self):
        field = self.field('Yiqun')
        self.bot.enter_text(field, 'Yiqun')
        self.assertEqual(field.get_attribute('value'), 'Yiqun')
        field.send_keys.assert_not_called()

    def test_duplicate_name_is_replaced_and_repeated_fill_is_idempotent(self):
        field = self.field('XuXu')
        self.bot.enter_text(field, 'Xu')
        self.bot.enter_text(field, 'Xu')
        self.assertEqual(field.get_attribute('value'), 'Xu')

    def test_windows_browser_uses_control_even_on_mac_host(self):
        field = self.field('Old')
        with patch('linkedineasyapply.sys.platform', 'darwin'):
            self.bot.enter_text(field, 'New')
        field.send_keys.assert_any_call(Keys.CONTROL, 'a')
        self.assertEqual(field.get_attribute('value'), 'New')

    def test_mac_browser_uses_command(self):
        self.bot.browser.capabilities = {'platformName': 'mac'}
        field = self.field('Old')
        self.bot.enter_text(field, 'New')
        field.send_keys.assert_any_call(Keys.COMMAND, 'a')

    def test_textarea_and_numeric_zero_replace_old_values(self):
        for tag, target in (('textarea', 'New answer'), ('input', 0)):
            with self.subTest(tag=tag):
                field = self.field('Old', tag)
                self.bot.enter_text(field, target)
                self.assertEqual(field.get_attribute('value'), str(target))

    def test_none_clears_without_typing_literal_none(self):
        field = self.field('Old')
        self.bot.enter_text(field, None)
        self.assertEqual(field.get_attribute('value'), '')

    def test_typeahead_can_force_input_events_without_appending(self):
        field = self.field('San Francisco')
        self.bot.enter_text(field, 'San Francisco', force=True)
        field.send_keys.assert_called_with('San Francisco')
        self.assertEqual(field.get_attribute('value'), 'San Francisco')

    def test_failed_clear_does_not_append_new_text(self):
        field = self.field('Old')
        field.send_keys.side_effect = None
        with patch('linkedineasyapply.WebDriverWait', side_effect=lambda element, *args, **kwargs:
                   WebDriverWait(element, 0.01, poll_frequency=0.001)):
            with self.assertRaises(TimeoutException):
                self.bot.enter_text(field, 'New')
        self.assertEqual(field.get_attribute('value'), 'Old')
        self.assertNotIn(('New',), [call.args for call in field.send_keys.call_args_list])


class NativeDialogTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        self.bot.browser = Mock()
        self.dialog = Mock(tag_name='dialog')
        self.marker = Mock()
        self.dialog.find_elements.side_effect = lambda by, selector: (
            [self.marker] if 'data-sdui-screen' in selector else []
        )

    def test_native_form_without_form_tag_routes_to_question_filling(self):
        self.bot.additional_questions = Mock()
        self.bot.send_resume = Mock()
        self.dialog.find_element.side_effect = NoSuchElementException()
        self.assertTrue(self.bot.fill_up(self.dialog))
        self.bot.additional_questions.assert_called_once_with(self.dialog, native=True)

    def test_native_dialog_found_without_classic_modal(self):
        self.bot._raise_if_daily_apply_limit = Mock()
        self.bot._shadow_elements = Mock(return_value=[])
        self.bot._visible_elements = Mock(side_effect=lambda context, by, selector: (
            [self.dialog] if 'dialog[open]' in selector else []
        ))
        self.assertIs(self.bot._find_easy_apply_context(timeout=1), self.dialog)

    def test_footer_action_ignores_back_and_upload(self):
        back, upload, next_button = (Mock(text=label) for label in ('Back', 'Upload resume', 'Next'))
        self.bot._visible_elements = Mock(side_effect=lambda context, by, selector: (
            [back, upload, next_button] if selector == 'footer button' else []
        ))
        self.assertIs(self.bot._find_easy_apply_primary_button(self.dialog), next_button)
        for button in (back, upload, next_button):
            button.click.assert_not_called()

    def test_review_can_expose_submit_without_form_fields(self):
        submit = Mock(text='Submit application')
        self.bot._visible_elements = Mock(side_effect=lambda context, by, selector: (
            [submit] if selector == 'footer button' else []
        ))
        self.assertIs(self.bot._find_easy_apply_primary_button(self.dialog), submit)
        submit.click.assert_not_called()

    def test_native_radio_uses_visible_choices_and_configured_work_authorization(self):
        for authorized, sponsorship, expected in ((True, False, 0), (True, True, 1), (False, False, 1)):
            with self.subTest(authorized=authorized, sponsorship=sponsorship):
                self.bot.checkboxes = {'legallyAuthorized': authorized, 'requireVisa': sponsorship}
                self.bot.customQuestions = {}
                self.bot._extract_question_text = Mock(return_value='Are you eligible to work without visa sponsorship?'.lower())
                self.bot._native_question_groups = Mock(return_value=[Mock()])
                question = self.bot._native_question_groups.return_value[0]
                question.find_elements.return_value = []
                options = [Mock(text='Yes'), Mock(text='No')]
                question.find_element.return_value.find_elements.return_value = options
                self.bot.additional_questions(self.dialog, native=True)
                options[expected].click.assert_called_once()
                options[1 - expected].click.assert_not_called()

    def test_native_eeo_does_not_guess_subtype_from_broad_config(self):
        self.bot.eeo = {'race': 'Asian'}
        self.bot.customQuestions = {}
        self.bot.ai_response_generator = Mock()
        self.bot._extract_question_text = Mock(return_value='i identify my ethnicity as')
        question = Mock()
        question.find_elements.return_value = []
        choices = [Mock(text='East Asian'), Mock(text='South Asian'), Mock(text="I don't wish to answer")]
        question.find_element.return_value.find_elements.return_value = choices
        self.bot._native_question_groups = Mock(return_value=[question])
        self.bot.additional_questions(self.dialog, native=True)
        choices[2].click.assert_called_once()
        choices[0].click.assert_not_called()
        choices[1].click.assert_not_called()
        self.bot.ai_response_generator.generate_response.assert_not_called()

    def test_native_error_text_excludes_hidden_page_source(self):
        self.bot.browser.page_source = 'enter a valid number'
        self.dialog.text = 'Review your application'
        self.assertEqual(self.bot._easy_apply_text(self.dialog), 'review your application')


if __name__ == '__main__':
    unittest.main()
