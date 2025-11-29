from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Post, Comment


class CommentReplyAPITests(APITestCase):
	"""Integration tests for replying to forum comments."""

	def setUp(self):
		User = get_user_model()
		self.author = User.objects.create_user(username='author', password='pass123')
		self.other_user = User.objects.create_user(username='other', password='pass123')
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
		self.assertEqual(response.data['post'], str(self.post.id))

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
