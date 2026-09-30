from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from traduzione import lingue
from traduzione.models import Lingua
from traduzione.servizio import traduci
from traduzione.tests import MotoreFinto

from .models import Post, Comment


class CommentReplyAPITests(APITestCase):
	"""Integration tests for replying to forum comments."""

	def setUp(self):
		User = get_user_model()
		# L'email e' la chiave di accesso ed e' unica: due utenti senza email
		# hanno entrambi la stringa vuota e il secondo non entra nel database.
		self.author = User.objects.create_user(
			username='author', email='author@test.com', password='pass123')
		self.other_user = User.objects.create_user(
			username='other', email='other@test.com', password='pass123')
		self.post = Post.objects.create(title='Post', description='Body', author=self.author)
		self.other_post = Post.objects.create(title='Another', description='Body', author=self.author)
		self.client.force_authenticate(self.author)
		self.comments_url = reverse('post-comments', args=[str(self.post.id)])

	def test_user_can_reply_to_comment(self):
		parent = Comment.objects.create(post=self.post, author=self.author, text='Parent comment')

		response = self.client.post(
			self.comments_url,
			{'text': 'Reply text', 'parent_id': str(parent.id)},
			format='json'
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['parent_id'], str(parent.id))
		self.assertEqual(str(response.data['post_id']), str(self.post.id))

	def test_cannot_reply_to_reply(self):
		parent = Comment.objects.create(post=self.post, author=self.author, text='Parent comment')
		reply = Comment.objects.create(post=self.post, author=self.author, text='First reply', parent=parent)

		response = self.client.post(
			self.comments_url,
			{'text': 'Nested reply', 'parent_id': str(reply.id)},
			format='json'
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('parent_id', response.data)

	def test_parent_must_belong_to_same_post(self):
		foreign_parent = Comment.objects.create(post=self.other_post, author=self.other_user, text='Other comment')

		response = self.client.post(
			self.comments_url,
			{'text': 'Invalid reply', 'parent_id': str(foreign_parent.id)},
			format='json'
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('parent_id', response.data)

	def test_post_detail_contains_nested_replies(self):
		parent = Comment.objects.create(post=self.post, author=self.author, text='Parent comment')
		Comment.objects.create(post=self.post, author=self.other_user, text='Reply comment', parent=parent)

		detail_url = reverse('post-detail', args=[str(self.post.id)])
		response = self.client.get(detail_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data['comments']), 1)
		self.assertEqual(len(response.data['comments'][0]['replies']), 1)


class ForumInLinguaDelLettoreTests(APITestCase):
	"""Il forum in inglese, chiesto come lo chiede il browser.

	E' il sintomo che l'utente ha segnalato: "cambio lingua ma rimane in
	italiano, e sembra anche i commenti". Le traduzioni c'erano; la lingua non
	arrivava, perche' `forumService` non aggiungeva `?locale=` e il backend
	leggeva solo quello.
	"""

	def setUp(self):
		User = get_user_model()
		Lingua.objects.all().delete()
		lingue.svuota_cache()
		Lingua.objects.create(codice='it', nome='Italiano', ordine=0)
		Lingua.objects.create(codice='en', nome='English', ordine=1)
		self.autore = User.objects.create_user(
			username='a', email='a@prova.it', password='prova12345')
		self.client.force_authenticate(self.autore)
		self.post = Post.objects.create(
			title='Il titolo', description='Il sommario',
			content_html='<p>Il corpo</p>', author=self.autore)
		self.commento = Comment.objects.create(
			post=self.post, author=self.autore, text='Il commento')
		for oggetto in (self.post, self.commento):
			traduci(oggetto, 'en', MotoreFinto())

	def inglese(self, url):
		return self.client.get(url, HTTP_ACCEPT_LANGUAGE='en-US,en;q=0.9').json()

	def test_il_post_si_legge_in_inglese(self):
		dati = self.inglese(reverse('post-detail', args=[str(self.post.id)]))
		self.assertEqual(dati['title'], 'IL TITOLO')
		# Il corpo non era mai stato tradotto prima di questa fase.
		self.assertEqual(dati['content_html'], '<p>IL CORPO</p>')
		self.assertEqual(dati['translated_from'], 'it')

	def test_anche_i_commenti(self):
		dati = self.inglese(reverse('post-comments', args=[str(self.post.id)]))
		voci = dati['results'] if isinstance(dati, dict) and 'results' in dati else dati
		self.assertEqual(voci[0]['text'], 'IL COMMENTO')
		self.assertEqual(voci[0]['translated_from'], 'it')

	def test_e_la_lista_dei_post(self):
		dati = self.inglese(reverse('post-list'))
		voci = dati['results'] if isinstance(dati, dict) and 'results' in dati else dati
		self.assertEqual(voci[0]['title'], 'IL TITOLO')

	def test_senza_intestazione_resta_l_originale(self):
		dati = self.client.get(reverse('post-detail', args=[str(self.post.id)])).json()
		self.assertEqual(dati['title'], 'Il titolo')
		self.assertIsNone(dati['translated_from'])

