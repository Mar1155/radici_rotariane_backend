from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Count, Prefetch
from .models import Post, Comment, PostTranslation
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    CommentSerializer,
    CommentCreateSerializer,
    PostTranslationSerializer,
)
from chat.services.translation import (
    TranslationProviderError,
    TranslationServiceNotConfigured,
    normalize_language_code,
    supported_languages,
    translate_text,
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
        queryset = Post.objects.annotate(
            comment_count=Count('comments', distinct=True)
        ).select_related('author').order_by('-created_at')

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

    @action(detail=True, methods=["post"])
    def translate(self, request, pk=None):
        post = self.get_object()
        target_language = request.data.get("target_language") or request.query_params.get(
            "target_language"
        )

        if not target_language:
            return Response(
                {"detail": "target_language è obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_language = normalize_language_code(target_language)
        if normalized_language not in supported_languages():
            return Response(
                {"detail": "Lingua di destinazione non supportata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = PostTranslation.objects.filter(
            post=post, target_language=normalized_language
        ).first()
        if existing:
            serializer = PostTranslationSerializer(existing)
            return Response(serializer.data)

        if not post.title.strip() and not post.description.strip():
             return Response(
                {"detail": "Il post è vuoto, impossibile tradurre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            title_result = translate_text(post.title, normalized_language)
            description_result = translate_text(post.description, normalized_language)
        except TranslationServiceNotConfigured:
            return Response(
                {"detail": "Nessun provider di traduzione configurato."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except TranslationProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        with transaction.atomic():
            translation, _created = PostTranslation.objects.get_or_create(
                post=post,
                target_language=normalized_language,
                defaults={
                    "translated_title": title_result.text,
                    "translated_description": description_result.text,
                    "provider": title_result.provider,
                    "detected_source_language": title_result.detected_source_language,
                },
            )

        serializer = PostTranslationSerializer(translation)
        http_status = status.HTTP_201_CREATED if _created else status.HTTP_200_OK
        return Response(serializer.data, status=http_status)

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

    @comments.mapping.post
    def add_comment(self, request, pk=None):
        """Add a comment to a post."""
        post = self.get_object()
        serializer = CommentCreateSerializer(data=request.data, context={'request': request, 'post': post})
        if serializer.is_valid():
            comment = serializer.save(post=post, author=request.user)
            return Response(
                CommentSerializer(comment, context=self.get_serializer_context()).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
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
