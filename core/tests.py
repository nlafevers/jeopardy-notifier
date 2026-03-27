from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
import pandas as pd

from .forms import UploadForm
from .services.parser import parse_roster
from .services.ranking import rank_employees


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


class RankingTests(TestCase):
    def test_fte_zero_employees_are_marked_do_not_rank_and_sorted_last(self):
        hours_df = pd.DataFrame(
            {'Jeopardy 7a-7a': [8, 0, 12]},
            index=['Alice Able', 'Bob Baker', 'Cara Clark'],
        )
        roster_df = pd.DataFrame(
            {
                'Qgenda Name': ['Alice Able', 'Bob Baker', 'Cara Clark'],
                'Email Name': ['Alice', 'Bob', 'Cara'],
                'FTE': [1.0, 0.0, 0.5],
            }
        )
        roster_df['Email Addresses'] = ['alice@example.com', 'bob@example.com', 'cara@example.com']

        ranked_df = rank_employees(hours_df, roster_df, 'Jeopardy 7a-7a')

        self.assertEqual(ranked_df['Qgenda'].tolist(), ['Cara Clark', 'Alice Able', 'Bob Baker'])
        self.assertEqual(ranked_df['Rank'].tolist(), ['1', '2', 'DNR'])
        self.assertEqual(ranked_df['DoNotRank'].tolist(), [False, False, True])

    def test_verification_defaults_do_not_select_dnr_rows(self):
        client = Client()
        session = client.session
        ranked_df = pd.DataFrame(
            [
                {
                    'Qgenda': 'Alice Able',
                    'EmailName': 'Alice',
                    'Hours': 8,
                    'FTE': 1.0,
                    'Score': 8.0,
                    'Rank': '1',
                    'DoNotRank': False,
                },
                {
                    'Qgenda': 'Bob Baker',
                    'EmailName': 'Bob',
                    'Hours': 0,
                    'FTE': 0.0,
                    'Score': None,
                    'Rank': 'DNR',
                    'DoNotRank': True,
                },
            ]
        )
        session['human_verified'] = True
        session['ranked_data'] = ranked_df.to_json(orient='split')
        session.save()

        response = client.get(reverse('verification'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Alice Able" checked', html=False)
        self.assertContains(response, 'value="Bob Baker"', html=False)
        self.assertNotContains(response, 'value="Bob Baker" checked', html=False)
        self.assertContains(response, 'DNR', html=False)


class ParserTests(TestCase):
    def test_parse_roster_requires_new_four_column_layout(self):
        roster_df = pd.DataFrame(
            {
                'Qgenda Name': ['Alice Able'],
                'Email Name': ['Alice'],
                'Email Addresses': ['alice@example.com'],
                'FTE': [1.0],
            }
        )

        roster_path = '/tmp/test-roster.xlsx'
        roster_df.to_excel(roster_path, index=False)

        with open(roster_path, 'rb') as roster_file:
            parsed_df = parse_roster(roster_file)

        self.assertEqual(parsed_df.columns.tolist(), ['Qgenda Name', 'EmailName', 'Email', 'FTE'])

    def test_parse_roster_rejects_old_five_column_layout(self):
        roster_df = pd.DataFrame(
            {
                'Qgenda Name': ['Alice Able'],
                'First Name': ['Alice'],
                'Last Name': ['Able'],
                'Email Addresses': ['alice@example.com'],
                'FTE': [1.0],
            }
        )

        roster_path = '/tmp/test-roster-old.xlsx'
        roster_df.to_excel(roster_path, index=False)

        with open(roster_path, 'rb') as roster_file:
            with self.assertRaises(ValueError):
                parse_roster(roster_file)
