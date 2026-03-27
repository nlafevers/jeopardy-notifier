from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .forms import UploadForm


def make_excel_upload(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        b'placeholder spreadsheet bytes',
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


class UploadFormTurnstileTests(TestCase):
    @override_settings(REQUIRE_TURNSTILE=True, TURNSTILE_SECRET_KEY='test-secret')
    def test_requires_turnstile_response_when_enabled(self):
        form = UploadForm(
            data={
                'assignment': 'Jeopardy 7a-7a',
                'custom_message': '',
                'turnstile_response': '',
            },
            files={
                'hours_report': make_excel_upload('hours.xlsx'),
                'roster': make_excel_upload('roster.xlsx'),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Please verify that you are human.', form.non_field_errors())

    @override_settings(REQUIRE_TURNSTILE=True, TURNSTILE_SECRET_KEY='test-secret')
    @patch('core.services.turnstile.verify_turnstile_token', return_value=True)
    def test_accepts_valid_turnstile_response_when_enabled(self, mock_verify):
        form = UploadForm(
            data={
                'assignment': 'Jeopardy 7a-7a',
                'custom_message': '',
                'turnstile_response': 'test-token',
            },
            files={
                'hours_report': make_excel_upload('hours.xlsx'),
                'roster': make_excel_upload('roster.xlsx'),
            },
        )

        self.assertTrue(form.is_valid())
        mock_verify.assert_called_once_with('test-token', 'test-secret')
