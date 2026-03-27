from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

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

    def test_rejects_non_excel_uploads(self):
        form = UploadForm(
            data={
                'assignment': 'Jeopardy 7a-7a',
                'custom_message': '',
                'turnstile_response': '',
            },
            files={
                'hours_report': SimpleUploadedFile('hours.txt', b'not excel', content_type='text/plain'),
                'roster': make_excel_upload('roster.xlsx'),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            'Hours Report must be an Excel spreadsheet (.xlsx, .xls, or .xlsm).',
            form.errors['hours_report'],
        )

    def test_rejects_oversized_uploads(self):
        form = UploadForm(
            data={
                'assignment': 'Jeopardy 7a-7a',
                'custom_message': '',
                'turnstile_response': '',
            },
            files={
                'hours_report': SimpleUploadedFile('hours.xlsx', b'a' * (5 * 1024 * 1024 + 1)),
                'roster': make_excel_upload('roster.xlsx'),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Hours Report must be 5 MB or smaller.', form.errors['hours_report'])


class WorkflowSecurityTests(TestCase):
    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_upload_get_clears_existing_workflow_session_data(self):
        client = Client()
        session = client.session
        session['ranked_data'] = 'cached'
        session['custom_message'] = 'message'
        session['email_count'] = 3
        session['human_verified'] = True
        session.save()

        response = client.get(reverse('upload'))

        self.assertEqual(response.status_code, 200)
        session = client.session
        self.assertNotIn('ranked_data', session)
        self.assertNotIn('custom_message', session)
        self.assertNotIn('email_count', session)
        self.assertNotIn('human_verified', session)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_send_emails_requires_post(self):
        client = Client()
        session = client.session
        session['human_verified'] = True
        session['ranked_data'] = '{}'
        session.save()

        response = client.get(reverse('send_emails'))

        self.assertEqual(response.status_code, 405)
