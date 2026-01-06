"""
Complete Working Django REST Framework API Example

This is a fully functional blog API demonstrating:
- Models with relationships
- ModelSerializers with nested data
- ViewSets with custom actions
- Token authentication
- Custom permissions
- Filtering and search
- Pagination
- Proper URL configuration

To use this example:
1. Create a new Django project
2. Copy the relevant sections to your project files
3. Run migrations
4. Create a superuser
5. Test the API

Project structure:
    myproject/
    ├── blog/
    │   ├── models.py        # Copy Model classes
    │   ├── serializers.py   # Copy Serializer classes
    │   ├── permissions.py   # Copy Permission classes
    │   ├── views.py         # Copy ViewSet classes
    │   └── urls.py          # Copy URL configuration
    └── config/
        ├── settings.py      # Copy REST_FRAMEWORK settings
        └── urls.py          # Include blog.urls
"""

# ============================================================================
# models.py
# ============================================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Category(models.Model):
    """Blog post category."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Blog post tag."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    """Blog post model."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(max_length=500, blank=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Comment(models.Model):
    """Comment on a blog post."""
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    content = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'


# ============================================================================
# serializers.py
# ============================================================================

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Category, Tag


class UserSerializer(serializers.ModelSerializer):
    """User serializer with post count."""
    posts_count = serializers.IntegerField(
        source='posts.count',
        read_only=True
    )
    comments_count = serializers.IntegerField(
        source='comments.count',
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'posts_count', 'comments_count'
        ]
        read_only_fields = ['id']


class TagSerializer(serializers.ModelSerializer):
    """Tag serializer."""
    posts_count = serializers.IntegerField(
        source='posts.count',
        read_only=True
    )

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'posts_count']
        read_only_fields = ['id', 'slug']


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer."""
    posts_count = serializers.IntegerField(
        source='posts.count',
        read_only=True
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'posts_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    """Comment serializer with author info."""
    author_username = serializers.CharField(
        source='author.username',
        read_only=True
    )
    replies_count = serializers.IntegerField(
        source='replies.count',
        read_only=True
    )
    # Nested replies (one level deep)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_username', 'parent',
            'content', 'is_approved', 'created_at', 'updated_at',
            'replies_count', 'replies'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_replies(self, obj):
        """Get comment replies (one level only)."""
        if obj.replies.exists():
            # Avoid infinite recursion by not including nested replies
            return CommentListSerializer(
                obj.replies.all(),
                many=True,
                context=self.context
            ).data
        return []

    def validate_parent(self, value):
        """Validate parent comment belongs to same post."""
        if value and value.post != self.initial_data.get('post'):
            raise serializers.ValidationError(
                "Parent comment must belong to the same post."
            )
        return value


class CommentListSerializer(serializers.ModelSerializer):
    """Simplified comment serializer for lists (no nested replies)."""
    author_username = serializers.CharField(
        source='author.username',
        read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            'id', 'author', 'author_username', 'content',
            'is_approved', 'created_at'
        ]
        read_only_fields = ['id', 'author', 'created_at']


class PostListSerializer(serializers.ModelSerializer):
    """Simplified post serializer for list views."""
    author_username = serializers.CharField(
        source='author.username',
        read_only=True
    )
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    comments_count = serializers.IntegerField(
        source='comments.count',
        read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'excerpt', 'author', 'author_username',
            'category', 'category_name', 'tags', 'status', 'published_at',
            'created_at', 'views_count', 'comments_count'
        ]
        read_only_fields = ['id', 'slug', 'author', 'created_at', 'views_count']


class PostDetailSerializer(serializers.ModelSerializer):
    """Detailed post serializer with all relationships."""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentListSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(
        source='comments.count',
        read_only=True
    )

    # Write-only fields for relationships
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt',
            'author', 'category', 'category_id', 'tags', 'tag_ids',
            'status', 'published_at', 'created_at', 'updated_at',
            'views_count', 'comments', 'comments_count'
        ]
        read_only_fields = [
            'id', 'slug', 'author', 'created_at', 'updated_at', 'views_count'
        ]

    def create(self, validated_data):
        """Create post with tags."""
        tags = validated_data.pop('tags', [])
        post = Post.objects.create(**validated_data)
        post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        """Update post with tags."""
        tags = validated_data.pop('tags', None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update tags if provided
        if tags is not None:
            instance.tags.set(tags)

        return instance

    def validate_title(self, value):
        """Validate title length."""
        if len(value) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long."
            )
        return value


# ============================================================================
# permissions.py
# ============================================================================

from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authors of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the author
        return obj.author == request.user


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow authors and admins to edit, others to read.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions for author or admin
        return obj.author == request.user or request.user.is_staff


# ============================================================================
# views.py
# ============================================================================

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Post, Comment, Category, Tag
from .serializers import (
    PostListSerializer, PostDetailSerializer,
    CommentSerializer, CategorySerializer,
    TagSerializer, UserSerializer
)
from .permissions import IsAuthorOrReadOnly, IsAuthorOrAdminOrReadOnly


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing posts.

    list: Get list of posts
    retrieve: Get a single post
    create: Create a new post
    update: Update a post
    partial_update: Partially update a post
    destroy: Delete a post

    Custom actions:
    - publish: Publish a draft post
    - my_posts: Get current user's posts
    - popular: Get most viewed posts
    """
    queryset = Post.objects.select_related(
        'author', 'category'
    ).prefetch_related('tags', 'comments')
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    ]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['created_at', 'updated_at', 'views_count', 'title']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use different serializers for list and detail."""
        if self.action == 'list':
            return PostListSerializer
        return PostDetailSerializer

    def get_queryset(self):
        """
        Filter queryset based on user and query parameters.
        Anonymous users only see published posts.
        """
        queryset = super().get_queryset()

        # Filter by status
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='published')

        # Filter by category
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Filter by tag
        tag_slug = self.request.query_params.get('tag', None)
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        # Filter by author
        author_username = self.request.query_params.get('author', None)
        if author_username:
            queryset = queryset.filter(author__username=author_username)

        return queryset

    def perform_create(self, serializer):
        """Set author to current user when creating."""
        serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving a post."""
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish a draft post.
        Only the author can publish their posts.
        """
        post = self.get_object()

        if post.status == 'published':
            return Response(
                {'detail': 'Post is already published.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        post.status = 'published'
        post.published_at = timezone.now()
        post.save()

        serializer = self.get_serializer(post)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_posts(self, request):
        """Get posts for the current authenticated user."""
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication required.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        posts = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(posts)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular posts by view count."""
        posts = self.get_queryset().order_by('-views_count')[:10]
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing comments."""
    queryset = Comment.objects.select_related('author', 'post').prefetch_related('replies')
    serializer_class = CommentSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrAdminOrReadOnly
    ]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_queryset(self):
        """Filter by post if specified."""
        queryset = super().get_queryset()

        post_id = self.request.query_params.get('post', None)
        if post_id:
            queryset = queryset.filter(post_id=post_id)

        # Only show approved comments to non-staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_approved=True)

        return queryset

    def perform_create(self, serializer):
        """Set author to current user when creating."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a comment (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin permission required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        comment = self.get_object()
        comment.is_approved = True
        comment.save()

        serializer = self.get_serializer(comment)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing categories."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing tags."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'


# ============================================================================
# urls.py (blog/urls.py)
# ============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, CommentViewSet, CategoryViewSet, TagViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]


# ============================================================================
# urls.py (config/urls.py - Project-level)
# ============================================================================

"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('blog.urls')),
    path('api/token/', obtain_auth_token, name='api_token_auth'),
    path('api-auth/', include('rest_framework.urls')),
]
"""


# ============================================================================
# settings.py (Add to your Django settings)
# ============================================================================

"""
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework.authtoken',

    # Local apps
    'blog',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
"""


# ============================================================================
# API USAGE EXAMPLES
# ============================================================================

"""
# 1. Get authentication token
curl -X POST http://127.0.0.1:8000/api/token/ \\
  -d "username=admin&password=yourpassword"

# Response: {"token": "YOUR_TOKEN_HERE"}

# 2. List all posts
curl http://127.0.0.1:8000/api/posts/

# 3. Get a specific post
curl http://127.0.0.1:8000/api/posts/1/

# 4. Create a post (authenticated)
curl -X POST http://127.0.0.1:8000/api/posts/ \\
  -H "Authorization: Token YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "My First Post",
    "content": "This is the content of my first post.",
    "excerpt": "A brief excerpt",
    "status": "published",
    "category_id": 1,
    "tag_ids": [1, 2]
  }'

# 5. Update a post
curl -X PUT http://127.0.0.1:8000/api/posts/1/ \\
  -H "Authorization: Token YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Updated Title",
    "content": "Updated content"
  }'

# 6. Delete a post
curl -X DELETE http://127.0.0.1:8000/api/posts/1/ \\
  -H "Authorization: Token YOUR_TOKEN"

# 7. Publish a draft post (custom action)
curl -X POST http://127.0.0.1:8000/api/posts/1/publish/ \\
  -H "Authorization: Token YOUR_TOKEN"

# 8. Get current user's posts
curl http://127.0.0.1:8000/api/posts/my_posts/ \\
  -H "Authorization: Token YOUR_TOKEN"

# 9. Get popular posts
curl http://127.0.0.1:8000/api/posts/popular/

# 10. Search posts
curl "http://127.0.0.1:8000/api/posts/?search=django"

# 11. Filter by category
curl "http://127.0.0.1:8000/api/posts/?category=technology"

# 12. Filter by tag
curl "http://127.0.0.1:8000/api/posts/?tag=python"

# 13. Order posts
curl "http://127.0.0.1:8000/api/posts/?ordering=-views_count"

# 14. Create a comment
curl -X POST http://127.0.0.1:8000/api/comments/ \\
  -H "Authorization: Token YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "post": 1,
    "content": "Great post!"
  }'

# 15. Reply to a comment
curl -X POST http://127.0.0.1:8000/api/comments/ \\
  -H "Authorization: Token YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "post": 1,
    "parent": 1,
    "content": "Thanks for your comment!"
  }'

# 16. Get comments for a post
curl "http://127.0.0.1:8000/api/comments/?post=1"

# 17. Create a category
curl -X POST http://127.0.0.1:8000/api/categories/ \\
  -H "Authorization: Token YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Technology",
    "description": "Posts about technology"
  }'

# 18. Create a tag
curl -X POST http://127.0.0.1:8000/api/tags/ \\
  -H "Authorization: Token YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Python"}'
"""
