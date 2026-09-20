from traduzione.conversazioni import traduci_in_sottofondo
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Count, Prefetch
from django.utils import timezone
from .models import Post, Comment, PostTranslation
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    CommentSerializer,
    CommentCreateSerializer,
    PostTranslationSerializer,
)
from common.richtext import sanitize_rich_text
from common.throttling import SoloInScrittura


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


class PostViewSet(SoloInScrittura, viewsets.ModelViewSet):
    """ViewSet for forum posts."""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination

    def get_queryset(self):
        queryset = Post.objects.annotate(
            comment_count=Count('comments', distinct=True)
        ).select_related('author').order_by('-created_at')

        scope = self.request.query_params.get('scope')
        if scope == 'mine':
            queryset = queryset.filter(author=self.request.user)
        elif scope == 'others':
            queryset = queryset.exclude(author=self.request.user)

        if getattr(self, 'action', None) == 'retrieve':
            reply_prefetch = Prefetch(
                'comments',
                queryset=Comment.objects.filter(parent__isnull=True)
                .select_related('author')
                .prefetch_related(
                    Prefetch(
                        'replies',
                        queryset=Comment.objects.select_related('author').order_by('created_at')
                    )
                )
                .order_by('created_at'),
                to_attr='prefetched_comments'
            )
            queryset = queryset.prefetch_related(reply_prefetch)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PostCreateSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        # Tradotto appena pubblicato, in sottofondo: chi scrive non aspetta.
        traduci_in_sottofondo('post', post)

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
        replies_prefetch = Prefetch(
            'replies',
            queryset=Comment.objects.select_related('author').order_by('created_at')
        )
        comments = post.comments.filter(parent__isnull=True).select_related('author').prefetch_related(
            replies_prefetch
        ).order_by('created_at')
        
        paginator = CommentPagination()
        page = paginator.paginate_queryset(comments, request)
        if page is not None:
            serializer = CommentSerializer(page, many=True, context=self.get_serializer_context())
            return paginator.get_paginated_response(serializer.data)
        
        serializer = CommentSerializer(comments, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_comments_read(self, request, pk=None):
        """Marks all comments on a post as read for the post owner."""
        post = self.get_object()
        if post.author != request.user:
            return Response({'status': 'ignored'})

        post.comments_read_at = timezone.now()
        post.save(update_fields=['comments_read_at'])
        return Response({'status': 'ok'})

    @comments.mapping.post
    def add_comment(self, request, pk=None):
        """Add a comment to a post."""
        post = self.get_object()
        serializer = CommentCreateSerializer(data=request.data, context={'request': request, 'post': post})
        if serializer.is_valid():
            comment = serializer.save(post=post, author=request.user)
            traduci_in_sottofondo('commento', comment)
            return Response(
                CommentSerializer(comment, context=self.get_serializer_context()).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(SoloInScrittura, viewsets.ModelViewSet):
    """ViewSet for comments (for individual comment operations)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    pagination_class = CommentPagination

    def get_queryset(self):
        replies_prefetch = Prefetch(
            'replies',
            queryset=Comment.objects.select_related('author').order_by('created_at')
        )
        return Comment.objects.select_related('author', 'post', 'parent').prefetch_related(replies_prefetch).order_by('created_at')

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
