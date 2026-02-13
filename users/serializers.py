import json
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Skill, SoftSkill, FocusArea
from .services.geocoding import GeocodingError, geocode_city


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


class FocusAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusArea
        fields = ['id', 'name', 'translations']


def _enrich_club_geodata(data: dict):
    city = str(data.get("club_city", "")).strip()
    country = str(data.get("club_country", "")).strip()
    if city:
        data["club_city"] = city
    if country:
        data["club_country"] = country

    if not city:
        return

    existing_lat = data.get("club_latitude")
    existing_lng = data.get("club_longitude")

    try:
        geodata = geocode_city(city=city, country=country or None)
        data["club_country"] = geodata["country"]
        data["club_latitude"] = geodata["latitude"]
        data["club_longitude"] = geodata["longitude"]
    except GeocodingError:
        # Fallback: keep manually provided coordinates if present.
        if existing_lat is None or existing_lng is None:
            raise serializers.ValidationError(
                {"club_city": "Impossibile geolocalizzare la citta selezionata."}
            )

    if data.get("club_city") and data.get("club_country"):
        data["location"] = f"{data['club_city']}, {data['club_country']}"


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    rotary_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    username = serializers.CharField(read_only=True)
    club = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(user_type='CLUB'),
        required=False,
        allow_null=True
    )
    location = serializers.CharField(required=False, allow_blank=True)
    club_latitude = serializers.FloatField(required=False, allow_null=True)
    club_longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'rotary_id', 'user_type', 'club_name', 'club_president', 'club_city', 'club_country',
            'club_district',
            'location', 'club_latitude', 'club_longitude',
            'club'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate(self, data):
        user_type = data.get('user_type', User.Types.NORMAL)
        if user_type == User.Types.NORMAL and (not data.get('first_name') or not data.get('last_name')):
            raise serializers.ValidationError({"name": "First name and last name are required."})
        if user_type == User.Types.NORMAL and not data.get('club'):
            raise serializers.ValidationError({"club": "Club is required for normal users."})
        if user_type == User.Types.CLUB:
            required_fields = {
                "club_name": "Club name is required.",
                "club_president": "Club president is required.",
                "club_city": "Club city is required.",
                "club_district": "Club district is required.",
            }
            errors = {}
            for field, message in required_fields.items():
                value = data.get(field)
                if not value or (isinstance(value, str) and not value.strip()):
                    errors[field] = message
            if errors:
                raise serializers.ValidationError(errors)
            _enrich_club_geodata(data)
        return data

    def validate_rotary_id(self, value):
        if value and User.objects.filter(rotary_id=value).exists():
            raise serializers.ValidationError("A user with this Rotarian ID already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['username'] = self.generate_username(
            validated_data.get('first_name', ''),
            validated_data.get('last_name', ''),
            validated_data.get('email', ''),
        )
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user

    def generate_username(self, first_name: str, last_name: str, email: str = "") -> str:
        base_slug = slugify(f"{first_name}.{last_name}") or slugify(email.split('@')[0]) or 'user'
        username = base_slug
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_slug}{counter}"
            counter += 1
        return username


class UserSearchSerializer(serializers.ModelSerializer):
    """Serializer for user search results."""
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    soft_skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    focus_areas = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'profession', 'sector', 'location', 'avatar', 'bio',
            'skills', 'soft_skills', 'focus_areas'
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
    focus_areas = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=FocusArea.objects.all(),
        required=False
    )
    club_members_count = serializers.SerializerMethodField()
    club_sister_clubs_count = serializers.SerializerMethodField()
    languages = JSONField(required=False)
    rotary_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rotary_id',
            'profession', 'sector', 'skills', 'soft_skills', 'focus_areas',
            'languages', 'offers_mentoring',
            'bio', 'club_name', 'location', 'avatar',
            'user_type',
            'is_email_verified',
            'is_superuser',
            'club_president', 'club_city', 'club_country', 'club_district',
            'club_latitude', 'club_longitude',
            'club_members_count', 'club_sister_clubs_count',
            'club'
        ]
        read_only_fields = ['username', 'email', 'club_members_count', 'club_sister_clubs_count', 'is_superuser', 'is_email_verified']

    def validate_rotary_id(self, value):
        if not value:
            return value

        queryset = User.objects.filter(rotary_id=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("A user with this Rotarian ID already exists.")
        return value

    def validate(self, data):
        user_type = data.get("user_type")
        if user_type is None and self.instance:
            user_type = self.instance.user_type

        if user_type == User.Types.CLUB:
            city = data.get("club_city", self.instance.club_city if self.instance else "")
            country = data.get("club_country", self.instance.club_country if self.instance else "")
            lat = data.get("club_latitude", self.instance.club_latitude if self.instance else None)
            lng = data.get("club_longitude", self.instance.club_longitude if self.instance else None)

            geodata_payload = dict(data)
            geodata_payload["club_city"] = city
            geodata_payload["club_country"] = country
            geodata_payload["club_latitude"] = lat
            geodata_payload["club_longitude"] = lng
            _enrich_club_geodata(geodata_payload)

            data["club_city"] = geodata_payload.get("club_city")
            data["club_country"] = geodata_payload.get("club_country")
            data["club_latitude"] = geodata_payload.get("club_latitude")
            data["club_longitude"] = geodata_payload.get("club_longitude")
            data["location"] = geodata_payload.get("location")

        return data

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
        
        for field in ['skills', 'soft_skills', 'focus_areas']:
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


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep the serializer aligned with email-based auth
        self.fields[self.username_field].required = True
        self.fields[self.username_field].allow_blank = False
        self.fields[self.username_field].allow_null = False

    def validate(self, attrs):
        email = attrs.get(self.username_field, '').strip().lower()

        if not email:
            raise AuthenticationFailed("Email is required for login.")

        attrs[self.username_field] = email
        data = super().validate(attrs)
        if not self.user.is_email_verified:
            raise AuthenticationFailed("Email non verificata. Controlla la tua posta e completa la verifica.")
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_code(self, value):
        cleaned = value.strip()
        if not cleaned.isdigit():
            raise serializers.ValidationError('Il codice deve contenere solo cifre.')
        return cleaned


class EmailVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class EmailVerificationConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_code(self, value):
        cleaned = value.strip()
        if not cleaned.isdigit():
            raise serializers.ValidationError('Il codice deve contenere solo cifre.')
        return cleaned
