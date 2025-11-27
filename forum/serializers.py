from rest_framework import serializers
from .models import Post, Comment


class AuthorSerializer(serializers.Serializer):
    """Serializer for author information."""
    id = serializers.IntegerField()
    username = serializers.CharField()


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comments."""
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'post', 'author', 'created_at', 'updated_at']


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments."""
    class Meta:
        model = Comment
        fields = ['text']


class PostListSerializer(serializers.ModelSerializer):
    """Serializer for listing posts (without full description)."""
    author = AuthorSerializer(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'author', 'comment_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'comment_count', 'created_at', 'updated_at']


class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for post detail view with comments."""
    author = AuthorSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'title', 'description', 'author', 'comment_count', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'comment_count', 'comments', 'created_at', 'updated_at']


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
