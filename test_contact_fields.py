import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By

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
        self.send_keys = Mock(side_effect=lambda value: self.attributes.update(value=str(value)))

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
        phone.send_keys.assert_called_once_with('4155550123')
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


if __name__ == '__main__':
    unittest.main()
