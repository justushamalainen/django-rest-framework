"""
Django REST Framework Views - Complete Working Examples

This file demonstrates all DRF view patterns with working code.
Copy-paste and modify for your needs.

Models used in examples:
- Article: Blog article with title, content, author, published status
- Comment: Comments on articles
- Tag: Tags for categorizing articles
"""

from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import (
    filters,
    mixins,
    status,
    viewsets,
)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveDestroyAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
    GenericAPIView,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView


# =============================================================================
# MODELS (for reference)
# =============================================================================

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    articles = models.ManyToManyField(Article, related_name='tags')


# =============================================================================
# SERIALIZERS (for reference)
# =============================================================================

from rest_framework import serializers


class ArticleSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'published', 'created_at']


class ArticleDetailSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'content', 'author', 'published',
            'featured', 'created_at', 'updated_at', 'comments_count'
        ]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Comment
        fields = ['id', 'content', 'author', 'created_at']


# =============================================================================
# PATTERN 1: APIView (Base Class - Maximum Control)
# =============================================================================

class ArticleListAPIView(APIView):
    """
    List all articles or create a new article.
    Use when you need full control over request/response cycle.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        """GET /api/articles/"""
        articles = Article.objects.filter(published=True)
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    def post(self, request):
        """POST /api/articles/"""
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArticleDetailAPIView(APIView):
    """
    Retrieve, update or delete an article.
    Demonstrates object-level operations with APIView.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk):
        """Helper to get object or 404"""
        try:
            obj = Article.objects.get(pk=pk)
            self.check_object_permissions(self.request, obj)
            return obj
        except Article.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Article not found")

    def get(self, request, pk):
        """GET /api/articles/{pk}/"""
        article = self.get_object(pk)
        serializer = ArticleDetailSerializer(article)
        return Response(serializer.data)

    def put(self, request, pk):
        """PUT /api/articles/{pk}/ - Full update"""
        article = self.get_object(pk)

        if article.author != request.user:
            raise PermissionDenied("You can only edit your own articles")

        serializer = ArticleSerializer(article, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """PATCH /api/articles/{pk}/ - Partial update"""
        article = self.get_object(pk)

        if article.author != request.user:
            raise PermissionDenied("You can only edit your own articles")

        serializer = ArticleSerializer(article, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """DELETE /api/articles/{pk}/"""
        article = self.get_object(pk)

        if article.author != request.user:
            raise PermissionDenied("You can only delete your own articles")

        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# PATTERN 2: Generic Views (Pre-built for CRUD)
# =============================================================================

# 2.1: ListAPIView - List collection
class ArticleListView(ListAPIView):
    """
    List all published articles.
    Supports filtering, searching, ordering out of the box.
    """
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']


# 2.2: CreateAPIView - Create instance
class ArticleCreateView(CreateAPIView):
    """
    Create a new article.
    Author is automatically set from request.user.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Override to set author"""
        serializer.save(author=self.request.user)


# 2.3: RetrieveAPIView - Get single instance
class ArticleDetailView(RetrieveAPIView):
    """
    Retrieve a single article by ID.
    Read-only view.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleDetailSerializer

    def get_queryset(self):
        """Optimize query with related data"""
        return Article.objects.select_related('author').prefetch_related('comments')


# 2.4: UpdateAPIView - Update instance
class ArticleUpdateView(UpdateAPIView):
    """
    Update an article (PUT/PATCH).
    Only owner can update.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        """Check ownership before update"""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You can only edit your own articles")
        serializer.save(updated_at=timezone.now())


# 2.5: DestroyAPIView - Delete instance
class ArticleDeleteView(DestroyAPIView):
    """
    Delete an article.
    Only owner can delete.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        """Check ownership before deletion"""
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own articles")
        instance.delete()


# 2.6: ListCreateAPIView - List + Create (Most Common!)
class ArticleListCreateView(ListCreateAPIView):
    """
    List all articles (GET) or create new article (POST).
    Most common pattern for collection endpoints.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']

    def get_queryset(self):
        """Filter by published status"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(published=True)
        return queryset

    def perform_create(self, serializer):
        """Set author on create"""
        serializer.save(author=self.request.user)


# 2.7: RetrieveUpdateDestroyAPIView - Full CRUD on single instance
class ArticleDetailFullView(RetrieveUpdateDestroyAPIView):
    """
    Complete CRUD operations on a single article.
    GET, PUT, PATCH, DELETE all in one view.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Use different serializers for read vs write"""
        if self.request.method == 'GET':
            return ArticleDetailSerializer
        return ArticleSerializer

    def perform_update(self, serializer):
        """Only owner can update"""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You can only edit your own articles")
        serializer.save()

    def perform_destroy(self, instance):
        """Only owner can delete"""
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own articles")
        instance.delete()


# =============================================================================
# PATTERN 3: Mixins (Compose Custom Views)
# =============================================================================

# 3.1: Custom combination with mixins
class ArticleListRetrieveView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericAPIView
):
    """
    Custom view with only list and retrieve (no create/update/delete).
    Demonstrates composing specific behaviors.
    """
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        if 'pk' in kwargs:
            return self.retrieve(request, *args, **kwargs)
        return self.list(request, *args, **kwargs)


# 3.2: Create + Destroy only (unusual but possible)
class ArticleCreateDestroyView(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericAPIView
):
    """
    Endpoint that only supports create and delete (no read/update).
    Demonstrates flexibility of mixins.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# =============================================================================
# PATTERN 4: ViewSets (With Router Support)
# =============================================================================

# 4.1: ModelViewSet - Full CRUD
class ArticleModelViewSet(viewsets.ModelViewSet):
    """
    Full CRUD ViewSet for articles.
    Provides list, create, retrieve, update, partial_update, destroy.

    Works with routers for automatic URL configuration:
        router.register(r'articles', ArticleModelViewSet)

    Generated URLs:
        GET    /articles/              → list()
        POST   /articles/              → create()
        GET    /articles/{pk}/         → retrieve()
        PUT    /articles/{pk}/         → update()
        PATCH  /articles/{pk}/         → partial_update()
        DELETE /articles/{pk}/         → destroy()
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'title']

    def get_queryset(self):
        """Filter based on authentication"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(published=True)
        return queryset

    def get_serializer_class(self):
        """Use detailed serializer for retrieve"""
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleSerializer

    def perform_create(self, serializer):
        """Set author on create"""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """Only owner can update"""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("You can only edit your own articles")
        serializer.save()

    def perform_destroy(self, instance):
        """Only owner can delete"""
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own articles")
        instance.delete()

    # Custom actions with @action decorator
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        GET /articles/featured/
        List action (operates on collection).
        """
        featured_articles = self.queryset.filter(featured=True, published=True)
        serializer = self.get_serializer(featured_articles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """
        POST /articles/{pk}/publish/
        Detail action (operates on single object).
        """
        article = self.get_object()

        if article.author != request.user:
            raise PermissionDenied("You can only publish your own articles")

        article.published = True
        article.save()
        return Response({'status': 'published'})

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """
        GET  /articles/{pk}/comments/  → List comments
        POST /articles/{pk}/comments/  → Add comment
        """
        article = self.get_object()

        if request.method == 'GET':
            comments = article.comments.all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(article=article, author=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def my_articles(self, request):
        """
        GET /articles/my_articles/
        User's own articles.
        """
        my_articles = self.queryset.filter(author=request.user)
        serializer = self.get_serializer(my_articles, many=True)
        return Response(serializer.data)


# 4.2: ReadOnlyModelViewSet - Read-only API
class ArticleReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet (list + retrieve only).
    Perfect for public APIs with no write operations.

    Provides: list(), retrieve()
    """
    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'content']


# 4.3: GenericViewSet with Custom Mixins
class ArticleCustomViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Custom ViewSet with only create, list, retrieve.
    No update or delete operations.

    Demonstrates composing custom behavior with ViewSets.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# 4.4: ViewSet with MethodMapper
class ArticleAdvancedViewSet(viewsets.ModelViewSet):
    """
    Advanced ViewSet demonstrating MethodMapper for @action.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @action(detail=False, methods=['get', 'post'])
    def drafts(self, request):
        """GET /articles/drafts/ - List drafts"""
        if request.method == 'GET':
            drafts = Article.objects.filter(published=False, author=request.user)
            serializer = self.get_serializer(drafts, many=True)
            return Response(serializer.data)

    @drafts.mapping.post
    def create_draft(self, request):
        """POST /articles/drafts/ - Create draft"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(published=False, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# PATTERN 5: Function-Based Views with @api_view
# =============================================================================

# 5.1: Simple GET endpoint
@api_view(['GET'])
def article_count(request):
    """
    GET /api/articles/count/
    Simple function-based view.
    """
    count = Article.objects.filter(published=True).count()
    return Response({'count': count})


# 5.2: GET and POST
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def article_list_function(request):
    """
    GET:  List all articles
    POST: Create new article
    """
    if request.method == 'GET':
        articles = Article.objects.filter(published=True)
        serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 5.3: Full CRUD in functions
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def article_detail_function(request, pk):
    """
    GET:    Retrieve article
    PUT:    Full update
    PATCH:  Partial update
    DELETE: Delete article
    """
    article = get_object_or_404(Article, pk=pk)

    if request.method == 'GET':
        serializer = ArticleDetailSerializer(article)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        if article.author != request.user:
            raise PermissionDenied("You can only edit your own articles")

        partial = request.method == 'PATCH'
        serializer = ArticleSerializer(article, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if article.author != request.user:
            raise PermissionDenied("You can only delete your own articles")

        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 5.4: Custom action endpoint
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_article_function(request, pk):
    """
    POST /api/articles/{pk}/publish/
    Custom action as function-based view.
    """
    article = get_object_or_404(Article, pk=pk)

    if article.author != request.user:
        raise PermissionDenied("You can only publish your own articles")

    article.published = True
    article.save()
    return Response({'status': 'published'})


# 5.5: Statistics endpoint
@api_view(['GET'])
@permission_classes([AllowAny])
def article_statistics(request):
    """
    GET /api/articles/statistics/
    Return article statistics.
    """
    total = Article.objects.count()
    published = Article.objects.filter(published=True).count()
    by_author = Article.objects.values('author__username').annotate(
        count=models.Count('id')
    ).order_by('-count')[:5]

    return Response({
        'total': total,
        'published': published,
        'draft': total - published,
        'top_authors': list(by_author)
    })


# =============================================================================
# URL CONFIGURATION EXAMPLES
# =============================================================================

"""
# urls.py for class-based views

from django.urls import path
from . import views

urlpatterns = [
    # APIView pattern
    path('articles/', views.ArticleListAPIView.as_view()),
    path('articles/<int:pk>/', views.ArticleDetailAPIView.as_view()),

    # Generic views pattern
    path('articles/list/', views.ArticleListCreateView.as_view()),
    path('articles/<int:pk>/detail/', views.ArticleDetailFullView.as_view()),

    # Function-based views
    path('articles/count/', views.article_count),
    path('articles/stats/', views.article_statistics),
    path('articles/<int:pk>/publish/', views.publish_article_function),
]


# urls.py for ViewSets with Router

from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'articles', views.ArticleModelViewSet)
router.register(r'readonly-articles', views.ArticleReadOnlyViewSet)

urlpatterns = router.urls

# Router generates:
# GET    /articles/              → list()
# POST   /articles/              → create()
# GET    /articles/{pk}/         → retrieve()
# PUT    /articles/{pk}/         → update()
# PATCH  /articles/{pk}/         → partial_update()
# DELETE /articles/{pk}/         → destroy()
# GET    /articles/featured/     → featured() custom action
# POST   /articles/{pk}/publish/ → publish() custom action
# GET    /articles/my_articles/  → my_articles() custom action
"""
