from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from chat.models import Chat, ChatParticipant

User = get_user_model()

class GemellaggioTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Clubs
        self.club1 = User.objects.create_user(
            username="club1", 
            email="club1@test.com", 
            password="password",
            user_type=User.Types.CLUB,
            club_name="Rotary Club Milano"
        )
        self.club2 = User.objects.create_user(
            username="club2", 
            email="club2@test.com", 
            password="password",
            user_type=User.Types.CLUB,
            club_name="Rotary Club Roma"
        )

        # Create Users linked to Club 1
        self.user1_c1 = User.objects.create_user(
            username="user1_c1", 
            email="u1c1@test.com", 
            password="password",
            user_type=User.Types.NORMAL,
            club=self.club1
        )
        self.user2_c1 = User.objects.create_user(
            username="user2_c1", 
            email="u2c1@test.com", 
            password="password",
            user_type=User.Types.NORMAL,
            club=self.club1
        )

        # Create Users linked to Club 2
        self.user1_c2 = User.objects.create_user(
            username="user1_c2", 
            email="u1c2@test.com", 
            password="password",
            user_type=User.Types.NORMAL,
            club=self.club2
        )

        # Create User with no club
        self.user_no_club = User.objects.create_user(
            username="user_no_club", 
            email="noclub@test.com", 
            password="password",
            user_type=User.Types.NORMAL
        )

    def test_create_gemellaggio_auto_participants(self):
        """
        Test that creating a Gemellaggio chat between clubs automatically adds
        all members of those clubs as participants.
        """
        # Create Gemellaggio Chat via Model (bypassing view restriction for this test logic check)
        # We use a club user as creator to be safe/consistent
        chat = Chat.create_group(
            name="Gemellaggio Milano-Roma",
            creator=self.club1,
            description="Test Gemellaggio",
            chat_type='gemellaggio',
            club_ids=[self.club1.id, self.club2.id]
        )

        # Verify Chat Type
        self.assertEqual(chat.chat_type, 'gemellaggio')

        # Verify Related Clubs
        self.assertEqual(chat.related_clubs.count(), 2)
        self.assertIn(self.club1, chat.related_clubs.all())
        self.assertIn(self.club2, chat.related_clubs.all())

        # Verify Participants
        participants = ChatParticipant.objects.filter(chat=chat)
        participant_users = [p.user for p in participants]

        # club1 (creator) should be admin
        creator_participant = participants.get(user=self.club1)
        self.assertEqual(creator_participant.role, 'admin')

        # club2 (partner) should be admin
        partner_participant = participants.get(user=self.club2)
        self.assertEqual(partner_participant.role, 'admin')

        # user2_c1 (club1 member) should be member
        self.assertIn(self.user2_c1, participant_users)
        
        # user1_c2 (club2 member) should be member
        self.assertIn(self.user1_c2, participant_users)

        # user_no_club should NOT be member
        self.assertNotIn(self.user_no_club, participant_users)

    def test_create_gemellaggio_permission_denied_for_normal_user(self):
        """
        Test that a NORMAL user cannot create a Gemellaggio chat via API.
        """
        self.client.force_authenticate(user=self.user1_c1)
        url = reverse('chat-create-group') # Assuming router generates this name, usually 'chat-create-group' or similar if using ViewSet custom action
        # Actually ViewSet actions are usually mapped like: /chat/create_group/
        # Let's check urls.py or just use the path if I can't find the name easily.
        # But 'chat-create-group' is standard for @action(detail=False) in DRF router if basename is 'chat'
        
        data = {
            "name": "Illegal Gemellaggio",
            "description": "Should fail",
            "chat_type": "gemellaggio",
            "club_ids": [self.club1.id, self.club2.id]
        }
        
        # I need to know the exact URL name. 
        # Let's assume /api/chat/create_group/ for now and use the path if needed.
        # Or better, check chat/urls.py
        
        response = self.client.post('/api/chats/create_group/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], "Solo i Club possono creare gemellaggi.")

    def test_create_gemellaggio_success_for_club_user(self):
        """
        Test that a CLUB user CAN create a Gemellaggio chat via API.
        """
        self.client.force_authenticate(user=self.club1)
        
        # The frontend sends only the OTHER club ID.
        # The backend should automatically add the creator's club ID.
        data = {
            "name": "Legal Gemellaggio",
            "description": "Should succeed",
            "chat_type": "gemellaggio",
            "club_ids": [self.club2.id]
        }
        
        response = self.client.post('/api/chats/create_group/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['chat_type'], 'gemellaggio')
        
        # Verify that both clubs are linked
        chat_id = response.data['id']
        chat = Chat.objects.get(id=chat_id)
        self.assertEqual(chat.related_clubs.count(), 2)
        self.assertIn(self.club1, chat.related_clubs.all())
        self.assertIn(self.club2, chat.related_clubs.all())

    def test_gemellaggio_signal_sync(self):
        """
        Test that a new user joining a club is automatically added to existing Gemellaggi.
        """
        # 1. Create Gemellaggio
        chat = Chat.create_group(
            name="Signal Test Gemellaggio",
            creator=self.club1,
            chat_type='gemellaggio',
            club_ids=[self.club1.id, self.club2.id]
        )

        # 2. Create a NEW user and assign to Club1
        new_user = User.objects.create_user(
            username="new_joiner",
            email="new@test.com",
            password="password",
            user_type=User.Types.NORMAL,
            club=self.club1
        )

        # 3. Verify user is added to chat via signal
        is_participant = ChatParticipant.objects.filter(chat=chat, user=new_user).exists()
        self.assertTrue(is_participant, "New club member should be auto-added to existing gemellaggio")

