from rest_framework import serializers
from .models import Post, Comment, PostTranslation


class AuthorSerializer(serializers.Serializer):
    """Serializer for author information."""
    id = serializers.IntegerField()
    username = serializers.CharField()


class ReplySerializer(serializers.ModelSerializer):
    """Serializer for replies."""
    author = AuthorSerializer(read_only=True)
    parent_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'parent_id', 'author', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'post', 'parent_id', 'author', 'created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comments with nested replies."""
    author = AuthorSerializer(read_only=True)
    parent_id = serializers.UUIDField(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'parent_id', 'author', 'text', 'created_at', 'updated_at', 'replies']
        read_only_fields = ['id', 'post', 'parent_id', 'author', 'created_at', 'updated_at', 'replies']


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
        fields = ['id', 'title', 'description', 'author', 'comment_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'comment_count', 'created_at', 'updated_at']


class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for post detail view with nested comments."""
    author = AuthorSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'author', 'comment_count', 'comments', 'created_at', 'updated_at']
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
        fields = ['id', 'title', 'description', 'author', 'comment_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_comment_count(self, obj):
        return 0


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
