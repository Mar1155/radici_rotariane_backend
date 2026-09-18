"""I controlli di deploy dicono quello che manca, e solo in produzione."""

from django.core.checks import run_checks
from django.test import TestCase, override_settings


def avvisi(**impostazioni):
    with override_settings(**impostazioni):
        return {a.id for a in run_checks(tags=['deploy'])}


class ControlliDiDeployTest(TestCase):
    PRODUZIONE = dict(
        DEBUG=False, EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST_USER='posta@esempio.it', CSRF_TRUSTED_ORIGINS=['https://a.it'],
        USE_S3=True, TRANSLATION_ENGINE='claude', ANTHROPIC_API_KEY='sk-finta',
        FRONTEND_BASE_URL='https://a.it', REVALIDATE_SECRET='segreto')

    def test_in_sviluppo_tacciono(self):
        """Con DEBUG acceso non manca niente per sbaglio: sarebbe solo rumore."""
        self.assertEqual(avvisi(DEBUG=True, EMAIL_HOST_USER='', USE_S3=False), set())

    def test_produzione_configurata_non_lamenta_niente(self):
        self.assertEqual(avvisi(**self.PRODUZIONE), set())

    def test_smtp_senza_account(self):
        self.assertIn('deploy.W001', avvisi(**{**self.PRODUZIONE, 'EMAIL_HOST_USER': ''}))

    def test_csrf_vuoto(self):
        self.assertIn('deploy.W002', avvisi(**{**self.PRODUZIONE, 'CSRF_TRUSTED_ORIGINS': []}))

    def test_senza_s3(self):
        self.assertIn('deploy.W003', avvisi(**{**self.PRODUZIONE, 'USE_S3': False}))

    def test_senza_chiave_di_traduzione(self):
        self.assertIn('deploy.W004', avvisi(**{**self.PRODUZIONE, 'ANTHROPIC_API_KEY': ''}))

    def test_senza_segreto_di_invalidazione(self):
        self.assertIn('deploy.W005', avvisi(**{**self.PRODUZIONE, 'REVALIDATE_SECRET': ''}))

    def test_un_motore_diverso_non_chiede_la_chiave_di_claude(self):
        self.assertNotIn('deploy.W004', avvisi(
            **{**self.PRODUZIONE, 'TRANSLATION_ENGINE': 'identita', 'ANTHROPIC_API_KEY': ''}))
