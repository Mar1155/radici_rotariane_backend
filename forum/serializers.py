from django.contrib.auth import get_user_model
from django.utils.html import strip_tags
from rest_framework import serializers
from .models import Post, Comment, PostTranslation
from .utils import sanitize_rich_text

User = get_user_model()


class AuthorSerializer(serializers.ModelSerializer):
    """Lightweight representation of a post/comment author."""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = fields


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comments with nested replies."""

    author = AuthorSerializer(read_only=True)
    post_id = serializers.UUIDField(read_only=True)
    parent_id = serializers.UUIDField(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'post_id',
            'parent_id',
            'author',
            'text',
            'replies',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_replies(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'replies' in obj._prefetched_objects_cache:
            replies = obj._prefetched_objects_cache['replies']
        else:
            replies = obj.replies.select_related('author').order_by('created_at')
        serializer = CommentSerializer(replies, many=True, context=self.context)
        return serializer.data


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments."""
    parent_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Comment
        fields = ['text', 'parent_id']

    def validate(self, attrs):
        parent_id = attrs.pop('parent_id', None)
        if parent_id:
            try:
                parent = Comment.objects.select_related('post').get(id=parent_id)
            except Comment.DoesNotExist:
                raise serializers.ValidationError({'parent_id': 'Commento padre non trovato.'})

            post = self.context.get('post')
            if not post or parent.post_id != post.id:
                raise serializers.ValidationError({'parent_id': 'Il commento padre appartiene a un post diverso.'})

            if parent.parent_id is not None:
                raise serializers.ValidationError({'parent_id': 'Non è possibile rispondere a una risposta.'})

            attrs['parent'] = parent

        return attrs

    def create(self, validated_data):
        parent = validated_data.pop('parent', None)
        return Comment.objects.create(parent=parent, **validated_data)


class PostListSerializer(serializers.ModelSerializer):
    """Serializer for listing posts (without full description)."""
    author = AuthorSerializer(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'content_html', 'author', 'comment_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'comment_count', 'created_at', 'updated_at']


class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for post detail view with nested comments."""
    author = AuthorSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'content_html', 'author', 'comment_count', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'comment_count', 'comments', 'created_at', 'updated_at']

    def get_comments(self, obj):
        top_level = getattr(obj, 'prefetched_comments', None)
        if top_level is None:
            top_level = obj.comments.filter(parent__isnull=True).select_related('author').prefetch_related(
                'replies__author'
            ).order_by('created_at')
        serializer = CommentSerializer(top_level, many=True, context=self.context)
        return serializer.data


class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating posts."""
    author = AuthorSerializer(read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'content_html', 'author', 'comment_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_comment_count(self, obj):
        return 0

    def validate(self, attrs):
        content_html_raw = attrs.get('content_html')
        description = attrs.get('description', '') or ''

        if content_html_raw is not None:
            cleaned_html = sanitize_rich_text(content_html_raw)
            attrs['content_html'] = cleaned_html
            if cleaned_html and not description.strip():
                attrs['description'] = strip_tags(cleaned_html).strip()
            description = attrs.get('description', '') or ''

        if not self.instance and not description.strip():
            raise serializers.ValidationError({'description': 'Il contenuto non può essere vuoto.'})

        return super().validate(attrs)


class PostTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTranslation
        fields = [
            'id',
            'post',
            'target_language',
            'translated_title',
            'translated_description',
            'provider',
            'detected_source_language',
            'created_at',
        ]
