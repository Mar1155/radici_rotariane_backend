import json
from rest_framework import serializers
from .models import User, Skill, SoftSkill


class JSONField(serializers.JSONField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                pass
        return super().to_internal_value(data)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'translations']


class SoftSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftSkill
        fields = ['id', 'name', 'translations']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    club = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(user_type='CLUB'),
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'user_type', 'club_name', 'club_city', 'club_country',
            'club_district',
            'club'
        ]

    def validate(self, data):
        user_type = data.get('user_type', User.Types.NORMAL)
        if user_type == User.Types.NORMAL and not data.get('club'):
            raise serializers.ValidationError({"club": "Club is required for normal users."})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserSearchSerializer(serializers.ModelSerializer):
    """Serializer for user search results."""
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    soft_skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'profession', 'sector', 'location', 'avatar', 'bio',
            'skills', 'soft_skills'
        ]
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile management."""
    skills = serializers.SlugRelatedField(
        many=True, 
        slug_field='name', 
        queryset=Skill.objects.all(),
        required=False
    )
    soft_skills = serializers.SlugRelatedField(
        many=True, 
        slug_field='name', 
        queryset=SoftSkill.objects.all(),
        required=False
    )
    club_members_count = serializers.SerializerMethodField()
    club_sister_clubs_count = serializers.SerializerMethodField()
    languages = JSONField(required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'profession', 'sector', 'skills', 'soft_skills',
            'languages', 'offers_mentoring',
            'bio', 'club_name', 'location', 'avatar',
            'user_type',
            'club_city', 'club_country', 'club_district',
            'club_latitude', 'club_longitude',
            'club_members_count', 'club_sister_clubs_count',
            'club'
        ]
        read_only_fields = ['username', 'email', 'club_members_count', 'club_sister_clubs_count']

    def get_club_members_count(self, obj):
        if obj.user_type != User.Types.CLUB:
            return 0
        if hasattr(obj, 'members_count'):
            return obj.members_count or 0
        return obj.members.filter(user_type=User.Types.NORMAL).count()

    def get_club_sister_clubs_count(self, obj):
        if obj.user_type != User.Types.CLUB:
            return 0
        if hasattr(obj, 'gemellaggi_count'):
            return obj.gemellaggi_count or 0
        return obj.gemellaggi_chats.filter(chat_type='gemellaggio').count()

    def to_internal_value(self, data):
        # Handle JSON strings for ManyToMany fields when using FormData
        # We need to make a mutable copy if it's a QueryDict
        if hasattr(data, 'copy'):
            mutable_data = data.copy()
        else:
            mutable_data = data
        
        for field in ['skills', 'soft_skills']:
            if field in mutable_data:
                value = mutable_data.get(field)
                if isinstance(value, str):
                    try:
                        # Try to parse as JSON array
                        parsed_value = json.loads(value)
                        if isinstance(parsed_value, list):
                            if hasattr(mutable_data, 'setlist'):
                                # For QueryDict, use setlist to avoid nesting
                                mutable_data.setlist(field, parsed_value)
                            else:
                                mutable_data[field] = parsed_value
                    except (ValueError, TypeError):
                        pass
                    
        return super().to_internal_value(mutable_data)
