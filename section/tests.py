from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Card, SavedCard


class ToggleSaveCardTests(APITestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='tester',
			email='tester@example.com',
			password='strong-password-123',
			first_name='Test',
			last_name='User',
		)

	def _create_card(self, section: str, tab: str, title: str, subtitle: str = 'Sottotitolo') -> Card:
		return Card.objects.create(
			section=section,
			tab=tab,
			title=title,
			subtitle=subtitle,
			tags=[],
			infoElementValues=[],
			is_published=True,
			author=self.user,
		)

	def test_toggle_save_allowed_when_save_is_required(self):
		self.client.force_authenticate(user=self.user)
		card = self._create_card(
			section='calendario-delle-radici',
			tab='main',
			title='Evento distrettuale',
		)

		url = reverse('toggle-save-card', kwargs={'slug': card.slug})
		save_response = self.client.post(url)
		self.assertEqual(save_response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(save_response.data['is_saved'])
		self.assertTrue(SavedCard.objects.filter(user=self.user, card=card).exists())

		unsave_response = self.client.post(url)
		self.assertEqual(unsave_response.status_code, status.HTTP_200_OK)
		self.assertFalse(unsave_response.data['is_saved'])
		self.assertFalse(SavedCard.objects.filter(user=self.user, card=card).exists())

	def test_toggle_save_blocked_when_save_is_not_required(self):
		self.client.force_authenticate(user=self.user)
		card = self._create_card(
			section='scopri-la-calabria',
			tab='consigli',
			title='Consiglio locale',
		)

		url = reverse('toggle-save-card', kwargs={'slug': card.slug})
		response = self.client.post(url)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(response.data['error'], 'Salvataggio non consentito per questa card')
		self.assertFalse(SavedCard.objects.filter(user=self.user, card=card).exists())
