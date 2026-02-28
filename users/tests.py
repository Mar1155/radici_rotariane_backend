from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Skill, FocusArea

class UserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User'
        )
        self.token_url = reverse('token_obtain_pair')
        self.me_url = '/api/users/me/' # Hardcoded to verify the path structure

    def test_me_endpoint(self):
        # Test unauthenticated
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Get token
        response = self.client.post(self.token_url, {
            'email': 'test@example.com',
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']

        # Test authenticated
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')


class SkillsSearchFiltersTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.request_user = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpassword',
            first_name='Req',
            last_name='User'
        )
        self.client.force_authenticate(user=self.request_user)

        self.skill = Skill.objects.create(name='Leadership')
        self.focus_macro_a = FocusArea.objects.create(
            name='Gestione di Progetti in generale',
            translations={'it': 'Gestione di Progetti in generale', 'code': 'A', 'macro_code': 'A', 'is_macro': True}
        )
        self.focus_detail_a1 = FocusArea.objects.create(
            name='Valutazione e monitoraggio',
            translations={'it': 'Valutazione e monitoraggio', 'code': 'A1', 'macro_code': 'A', 'is_macro': False}
        )
        self.focus_macro_b = FocusArea.objects.create(
            name='Rotary Grants',
            translations={'it': 'Rotary Grants', 'code': 'B', 'macro_code': 'B', 'is_macro': True}
        )
        self.focus_detail_b1 = FocusArea.objects.create(
            name='Processi di sviluppo di Rotary Grants e loro compilazione',
            translations={'it': 'Processi di sviluppo di Rotary Grants e loro compilazione', 'code': 'B1', 'macro_code': 'B', 'is_macro': False}
        )

        self.engineer_user = User.objects.create_user(
            username='engineer',
            email='engineer@example.com',
            password='testpassword',
            first_name='Anna',
            last_name='Rossi',
            profession='Engineer'
        )
        self.engineer_user.skills.add(self.skill)
        self.engineer_user.focus_areas.add(self.focus_detail_a1)

        self.lawyer_user = User.objects.create_user(
            username='lawyer',
            email='lawyer@example.com',
            password='testpassword',
            first_name='Luca',
            last_name='Bianchi',
            profession='Lawyer'
        )
        self.lawyer_user.skills.add(self.skill)
        self.lawyer_user.focus_areas.add(self.focus_detail_b1)

    def test_skills_filter_options_returns_hierarchical_focus_areas_and_professions(self):
        response = self.client.get(
            f'/api/users/skills-filter-options/?macro_focus_area_id={self.focus_macro_a.id}&focus_area_id={self.focus_detail_a1.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['id'] == self.focus_macro_a.id for item in response.data['macro_focus_areas']))
        self.assertTrue(any(item['id'] == self.focus_detail_a1.id for item in response.data['focus_areas']))
        self.assertEqual(response.data['professions'], ['Engineer'])

    def test_skills_search_filters_by_focus_area_id_and_profession(self):
        response = self.client.get(f'/api/users/skills/?focus_area_id={self.focus_detail_a1.id}&profession=Engineer')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.engineer_user.id)

    def test_skills_search_filters_by_macro_focus_area_id(self):
        response = self.client.get(f'/api/users/skills/?macro_focus_area_id={self.focus_macro_a.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.engineer_user.id)
