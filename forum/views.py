from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count
from .models import Post, Comment
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    CommentSerializer,
    CommentCreateSerializer,
)


class PostPagination(PageNumberPagination):
    """Pagination for posts - 15 per page."""
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50


class CommentPagination(PageNumberPagination):
    """Pagination for comments - 20 per page."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PostViewSet(viewsets.ModelViewSet):
    """ViewSet for forum posts."""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination

    def get_queryset(self):
        return Post.objects.annotate(
            comment_count=Count('comments')
        ).select_related('author').order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PostCreateSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        # Only author can delete their post
        if post.author != request.user:
            return Response(
                {'error': 'You can only delete your own posts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        # Only author can update their post
        if post.author != request.user:
            return Response(
                {'error': 'You can only edit your own posts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get paginated comments for a post."""
        post = self.get_object()
        comments = post.comments.select_related('author').order_by('created_at')
        
        paginator = CommentPagination()
        page = paginator.paginate_queryset(comments, request)
        if page is not None:
            serializer = CommentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    @comments.mapping.post
    def add_comment(self, request, pk=None):
        """Add a comment to a post."""
        post = self.get_object()
        serializer = CommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(post=post, author=request.user)
            return Response(
                CommentSerializer(comment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for comments (for individual comment operations)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    pagination_class = CommentPagination

    def get_queryset(self):
        return Comment.objects.select_related('author', 'post').order_by('created_at')

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        # Only author can delete their comment
        if comment.author != request.user:
            return Response(
                {'error': 'You can only delete your own comments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        # Only author can update their comment
        if comment.author != request.user:
            return Response(
                {'error': 'You can only edit your own comments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
