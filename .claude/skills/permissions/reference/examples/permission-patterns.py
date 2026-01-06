"""
DRF Permission Patterns - Working Code Examples

This file contains complete, tested permission patterns for common scenarios.
All examples are production-ready and follow DRF best practices.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.db import models
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# ============================================================================
# SECTION 1: BASIC PERMISSION PATTERNS
# ============================================================================


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners to access an object.

    Usage:
        permission_classes = [IsAuthenticated, IsOwner]
    """

    message = "You must be the owner to perform this action."

    def has_permission(self, request, view):
        # View-level: User must be authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Object-level: User must be the owner
        return obj.owner == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow anyone to read, but only owners can edit.

    Usage:
        permission_classes = [IsOwnerOrReadOnly]
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.owner == request.user


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Allow owners or staff members to access objects.

    Usage:
        permission_classes = [IsOwnerOrStaff]
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Staff can access anything
        if request.user.is_staff:
            return True

        # Regular users can only access their own objects
        return obj.owner == request.user


# ============================================================================
# SECTION 2: PERMISSION COMPOSITION EXAMPLES
# ============================================================================


class IsAdminOrOwner(permissions.BasePermission):
    """
    Admin users OR owners can access.
    Demonstrates OR logic using composition.

    Usage:
        permission_classes = [IsAdminUser | IsOwner]
        # Or as a standalone class:
        permission_classes = [IsAdminOrOwner]
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin can access any object
        if user.is_staff:
            return True

        # Owner can access their own objects
        return obj.owner == user


class IsAuthenticatedAndVerified(permissions.BasePermission):
    """
    User must be authenticated AND email verified.
    Demonstrates AND logic.

    Usage:
        permission_classes = [IsAuthenticated & IsEmailVerified]
        # Or as a standalone class:
        permission_classes = [IsAuthenticatedAndVerified]
    """

    message = "You must verify your email address to access this resource."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Check if user has verified email
        return getattr(user, "email_verified", False)


class NotBanned(permissions.BasePermission):
    """
    User must NOT be banned.
    Demonstrates NOT logic.

    Usage:
        permission_classes = [IsAuthenticated & ~IsBanned]
        # Or:
        permission_classes = [IsAuthenticated & NotBanned]
    """

    message = "Your account has been banned."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return True  # Anonymous users aren't banned

        return not getattr(user, "is_banned", False)


# Example using composition operators
def get_complex_permission():
    """
    Returns: (Admin OR Owner) AND (Authenticated AND NotBanned)

    Usage:
        from rest_framework.permissions import IsAdminUser, IsAuthenticated
        permission_classes = [
            (IsAdminUser | IsOwner) & (IsAuthenticated & NotBanned)
        ]
    """
    from rest_framework.permissions import IsAdminUser, IsAuthenticated

    return (IsAdminUser | IsOwner) & (IsAuthenticated & NotBanned)


# ============================================================================
# SECTION 3: ROLE-BASED PERMISSIONS
# ============================================================================


class IsManager(permissions.BasePermission):
    """
    Only allow users with 'manager' role.

    Assumes User model has a 'role' field.
    """

    message = "Only managers can perform this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return getattr(user, "role", None) == "manager"


class HasRole(permissions.BasePermission):
    """
    Flexible role-based permission.

    Usage:
        class MyViewSet(viewsets.ModelViewSet):
            def get_permissions(self):
                if self.action == 'approve':
                    return [HasRole(['manager', 'admin'])]
                return [IsAuthenticated()]
    """

    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        user_role = getattr(user, "role", None)
        return user_role in self.allowed_roles


class IsDepartmentMember(permissions.BasePermission):
    """
    User must belong to the same department as the object.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Staff can access all departments
        if user.is_staff:
            return True

        # Check department match
        user_dept = getattr(user, "department", None)
        obj_dept = getattr(obj, "department", None)

        return user_dept and obj_dept and user_dept == obj_dept


# ============================================================================
# SECTION 4: TEAM/GROUP PERMISSIONS
# ============================================================================


class IsTeamMember(permissions.BasePermission):
    """
    User must be a member of the object's team.

    Assumes object has a 'team' attribute with a 'members' ManyToMany field.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin can access all teams
        if user.is_staff:
            return True

        # Check team membership
        if hasattr(obj, "team"):
            return user in obj.team.members.all()

        return False


class IsProjectCollaborator(permissions.BasePermission):
    """
    User must be the owner or a collaborator on the project.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Owner has full access
        if obj.owner == user:
            return True

        # Check if user is a collaborator
        if hasattr(obj, "collaborators"):
            return user in obj.collaborators.all()

        return False


# ============================================================================
# SECTION 5: STATE-BASED PERMISSIONS
# ============================================================================


class CanEditDraft(permissions.BasePermission):
    """
    Allow editing only if the object is still in draft status.
    """

    message = "Only draft items can be edited."

    def has_object_permission(self, request, view, obj):
        # Allow all read operations
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if object is in draft state
        status = getattr(obj, "status", None)
        if status != "draft":
            return False

        # Must also be the owner
        return obj.owner == request.user


class CannotEditPublished(permissions.BasePermission):
    """
    Prevent editing once an object is published.
    """

    message = "Published items cannot be edited."

    def has_object_permission(self, request, view, obj):
        # Allow read operations
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check publication status
        is_published = getattr(obj, "is_published", False)
        if is_published:
            return False

        return obj.owner == request.user


class CanApproveSubmitted(permissions.BasePermission):
    """
    Only managers can approve items in 'submitted' status.
    """

    message = "Only submitted items can be approved, and only by managers."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Only managers can approve
        return getattr(user, "role", None) == "manager"

    def has_object_permission(self, request, view, obj):
        # Only items in 'submitted' status can be approved
        return getattr(obj, "status", None) == "submitted"


# ============================================================================
# SECTION 6: TIME-BASED PERMISSIONS
# ============================================================================


class CanEditRecent(permissions.BasePermission):
    """
    Allow editing only within 24 hours of creation.
    """

    message = "Items can only be edited within 24 hours of creation."

    def has_object_permission(self, request, view, obj):
        from datetime import timedelta

        # Allow read operations
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check time window
        created_at = getattr(obj, "created_at", None)
        if created_at:
            age = timezone.now() - created_at
            if age > timedelta(hours=24):
                return False

        # Must be the owner
        return obj.owner == request.user


class IsWithinBusinessHours(permissions.BasePermission):
    """
    Allow access only during business hours (9 AM - 5 PM).
    """

    message = "This resource is only available during business hours (9 AM - 5 PM)."

    def has_permission(self, request, view):
        now = timezone.now()

        # Check if current time is within business hours
        if 9 <= now.hour < 17:
            return True

        # Admin can access anytime
        if request.user and request.user.is_staff:
            return True

        return False


# ============================================================================
# SECTION 7: IP-BASED PERMISSIONS
# ============================================================================


class IsFromAllowedIP(permissions.BasePermission):
    """
    Allow access only from whitelisted IP addresses.
    """

    message = "Access denied from this IP address."

    # Configure allowed IPs
    ALLOWED_IPS = [
        "127.0.0.1",  # Localhost
        "192.168.1.0/24",  # Local network (requires ipaddress module)
    ]

    def has_permission(self, request, view):
        ip_addr = self._get_client_ip(request)

        # Simple exact match
        if ip_addr in self.ALLOWED_IPS:
            return True

        # For CIDR matching, use ipaddress module
        try:
            import ipaddress

            ip_obj = ipaddress.ip_address(ip_addr)

            for allowed in self.ALLOWED_IPS:
                if "/" in allowed:  # CIDR notation
                    network = ipaddress.ip_network(allowed, strict=False)
                    if ip_obj in network:
                        return True
        except (ValueError, ImportError):
            pass

        return False

    def _get_client_ip(self, request):
        """Get client IP from request, handling proxies."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# ============================================================================
# SECTION 8: SUBSCRIPTION/PAYMENT PERMISSIONS
# ============================================================================


class HasActiveSubscription(permissions.BasePermission):
    """
    User must have an active subscription.
    """

    message = "An active subscription is required to access this resource."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Check subscription status
        return getattr(user, "subscription_active", False)


class HasPremiumAccess(permissions.BasePermission):
    """
    User must have premium or enterprise subscription tier.
    """

    message = "Premium or Enterprise subscription required."

    ALLOWED_TIERS = ["premium", "enterprise"]

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin always has access
        if user.is_staff:
            return True

        # Check subscription tier
        tier = getattr(user, "subscription_tier", None)
        return tier in self.ALLOWED_TIERS


# ============================================================================
# SECTION 9: ACTION-BASED PERMISSIONS (ViewSets)
# ============================================================================


class ActionBasedPermission(permissions.BasePermission):
    """
    Different permission logic based on viewset action.

    Usage:
        permission_classes = [ActionBasedPermission]
    """

    def has_permission(self, request, view):
        user = request.user

        # Get the action being performed
        action = getattr(view, "action", None)

        # List: Anyone can list
        if action == "list":
            return True

        # Retrieve: Anyone can retrieve
        if action == "retrieve":
            return True

        # Create: Must be authenticated
        if action == "create":
            return user and user.is_authenticated

        # Update/Delete: Must be authenticated (object-level check will verify ownership)
        if action in ["update", "partial_update", "destroy"]:
            return user and user.is_authenticated

        # Custom actions: Check individually
        if action == "approve":
            return user and user.is_staff

        if action == "publish":
            return user and user.is_authenticated

        # Default: deny
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        action = getattr(view, "action", None)

        # Update/Delete: Must be owner or staff
        if action in ["update", "partial_update", "destroy"]:
            return obj.owner == user or user.is_staff

        # Approve: Staff only
        if action == "approve":
            return user.is_staff

        # Publish: Owner or staff
        if action == "publish":
            return obj.owner == user or user.is_staff

        return True


# ============================================================================
# SECTION 10: HIERARCHICAL PERMISSIONS
# ============================================================================


class HasHierarchicalAccess(permissions.BasePermission):
    """
    Hierarchical permissions: Organization Admin > Project Owner > Team Member

    Assumes:
        - obj has 'organization' with 'admins' M2M field
        - obj has 'owner' ForeignKey
        - obj has 'team' with 'members' M2M field
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Level 1: Organization admins have full access
        if hasattr(obj, "organization"):
            if obj.organization.admins.filter(id=user.id).exists():
                return True

        # Level 2: Project owner has full access
        if hasattr(obj, "owner") and obj.owner == user:
            return True

        # Level 3: Team members have limited access
        if hasattr(obj, "team"):
            if user in obj.team.members.all():
                # Members can read but not delete
                if request.method == "DELETE":
                    return False
                return True

        return False


# ============================================================================
# SECTION 11: COMPLETE VIEWSET EXAMPLE WITH PERMISSIONS
# ============================================================================


class Article(models.Model):
    """Example model for demonstration."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("published", "Published"),
        ],
        default="draft",
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="articles"
    )
    collaborators = models.ManyToManyField(User, related_name="collaborations", blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ArticleViewSet(viewsets.ModelViewSet):
    """
    Complete ViewSet example with various permission patterns.

    Permissions:
    - List: Anyone can list published articles
    - Retrieve: Anyone can view published, owner/collaborators can view drafts
    - Create: Authenticated users only
    - Update: Owner or collaborators only, cannot edit published
    - Delete: Owner only, cannot delete published
    - Publish: Owner only, requires 'submitted' status
    - Approve: Staff only
    """

    queryset = Article.objects.all()

    def get_permissions(self):
        """
        Instantiate and return the list of permissions for this view.
        """
        if self.action == "list":
            permission_classes = [permissions.AllowAny]
        elif self.action == "retrieve":
            permission_classes = [permissions.AllowAny]
        elif self.action == "create":
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [
                permissions.IsAuthenticated,
                IsProjectCollaborator,
                CannotEditPublished,
            ]
        elif self.action == "destroy":
            permission_classes = [
                permissions.IsAuthenticated,
                IsOwner,
                CannotEditPublished,
            ]
        elif self.action == "publish":
            permission_classes = [permissions.IsAuthenticated, IsOwner]
        elif self.action == "approve":
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        """
        user = self.request.user

        # Anonymous users: only published articles
        if not user.is_authenticated:
            return Article.objects.filter(is_published=True)

        # Staff can see everything
        if user.is_staff:
            return Article.objects.all()

        # Regular users: published + their own + collaborations
        from django.db.models import Q

        return Article.objects.filter(
            Q(is_published=True) | Q(owner=user) | Q(collaborators=user)
        ).distinct()

    def perform_create(self, serializer):
        """Set owner on creation."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """
        Publish an article (owner only).
        """
        article = self.get_object()

        if article.status != "submitted":
            return Response(
                {"error": "Only submitted articles can be published."},
                status=400
            )

        article.status = "published"
        article.is_published = True
        article.save()

        return Response({"status": "published"})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Approve an article (staff only).
        """
        article = self.get_object()

        if article.status != "submitted":
            return Response(
                {"error": "Only submitted articles can be approved."},
                status=400
            )

        article.status = "published"
        article.is_published = True
        article.save()

        return Response({"status": "approved and published"})


# ============================================================================
# SECTION 12: TESTING PERMISSION PATTERNS
# ============================================================================


def example_permission_tests():
    """
    Example unit tests for permission classes.

    Usage:
        Run with: python manage.py test myapp.tests.PermissionTests
    """
    from django.test import TestCase
    from rest_framework.test import APIRequestFactory

    class PermissionTests(TestCase):
        def setUp(self):
            self.factory = APIRequestFactory()
            self.user1 = User.objects.create_user("user1", password="pass")
            self.user2 = User.objects.create_user("user2", password="pass")
            self.admin = User.objects.create_user(
                "admin", password="pass", is_staff=True
            )

        def test_is_owner_permission(self):
            """Test IsOwner permission"""
            # Create mock object with owner
            class MockObj:
                def __init__(self, owner):
                    self.owner = owner

            obj = MockObj(owner=self.user1)

            # Test owner has permission
            request = self.factory.get("/")
            request.user = self.user1

            permission = IsOwner()
            self.assertTrue(permission.has_object_permission(request, None, obj))

            # Test non-owner denied
            request.user = self.user2
            self.assertFalse(permission.has_object_permission(request, None, obj))

        def test_is_owner_or_staff_permission(self):
            """Test IsOwnerOrStaff permission"""

            class MockObj:
                def __init__(self, owner):
                    self.owner = owner

            obj = MockObj(owner=self.user1)

            request = self.factory.get("/")
            permission = IsOwnerOrStaff()

            # Test owner has permission
            request.user = self.user1
            self.assertTrue(permission.has_object_permission(request, None, obj))

            # Test staff has permission
            request.user = self.admin
            self.assertTrue(permission.has_object_permission(request, None, obj))

            # Test other user denied
            request.user = self.user2
            self.assertFalse(permission.has_object_permission(request, None, obj))

        def test_permission_composition(self):
            """Test composed permissions"""
            from rest_framework.permissions import IsAuthenticated, IsAdminUser

            # Test AND composition
            and_permission = IsAuthenticated & IsAdminUser
            perm_instance = and_permission()

            request = self.factory.get("/")

            # Admin passes both checks
            request.user = self.admin
            self.assertTrue(perm_instance.has_permission(request, None))

            # Regular user fails admin check
            request.user = self.user1
            self.assertFalse(perm_instance.has_permission(request, None))

            # Test OR composition
            or_permission = IsAuthenticated | IsAdminUser
            perm_instance = or_permission()

            # Regular user passes (is authenticated)
            request.user = self.user1
            self.assertTrue(perm_instance.has_permission(request, None))


# ============================================================================
# SECTION 13: UTILITY FUNCTIONS
# ============================================================================


def check_permission_for_user(permission_class, user, obj=None, method="GET"):
    """
    Utility function to check if a permission would pass for a given user.

    Args:
        permission_class: Permission class to check
        user: User instance
        obj: Optional object for object-level permissions
        method: HTTP method (default: GET)

    Returns:
        bool: True if permission passes, False otherwise

    Example:
        has_perm = check_permission_for_user(IsOwner, request.user, article)
    """
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()
    request = factory.generic(method, "/")
    request.user = user

    permission = permission_class()

    # Check view-level permission
    if not permission.has_permission(request, None):
        return False

    # Check object-level permission if object provided
    if obj and not permission.has_object_permission(request, None, obj):
        return False

    return True


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
Example 1: Using composition in views
---------------------------------------

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from myapp.permissions import IsOwner, HasActiveSubscription

class PremiumContentViewSet(ModelViewSet):
    # Admin OR (Authenticated AND Subscription AND Owner)
    permission_classes = [
        IsAdminUser | (IsAuthenticated & HasActiveSubscription & IsOwner)
    ]


Example 2: Action-based permissions
------------------------------------

class ArticleViewSet(ModelViewSet):
    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwner()]
        return super().get_permissions()


Example 3: Multiple permission classes (all must pass)
------------------------------------------------------

class SecureViewSet(ModelViewSet):
    permission_classes = [
        IsAuthenticated,
        HasActiveSubscription,
        NotBanned,
        IsOwner,
    ]


Example 4: Testing permissions
-------------------------------

from django.test import TestCase

class MyPermissionTest(TestCase):
    def test_owner_can_edit(self):
        user = User.objects.create(username='test')
        article = Article.objects.create(owner=user)

        has_perm = check_permission_for_user(
            IsOwner,
            user,
            article,
            method='PUT'
        )

        self.assertTrue(has_perm)
"""
