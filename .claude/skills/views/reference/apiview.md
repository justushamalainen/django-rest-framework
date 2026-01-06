# APIView - For Custom Logic

Use APIView when you need complete control over the request/response cycle. For standard CRUD, use ViewSets or Generic Views instead.

## When to Use APIView

✅ Multiple models in one endpoint
✅ Complex business logic that doesn't fit CRUD
✅ Non-standard HTTP behavior
❌ Standard CRUD operations (use ViewSet instead)

## Basic Example

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class CustomEndpoint(APIView):
    """
    Use APIView for custom logic.
    Implement HTTP method handlers: get(), post(), put(), patch(), delete()
    """

    def get(self, request):
        # Your custom logic here
        return Response({'message': 'Hello'})

    def post(self, request):
        data = request.data
        # Process data
        return Response(data, status=status.HTTP_201_CREATED)
```

## Setting Policy Classes

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

class ProtectedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'user': request.user.username})
```

## Request and Response Objects

```python
def get(self, request):
    # Request attributes:
    request.data            # Parsed request body
    request.query_params    # Query parameters
    request.user            # Authenticated user
    request.method          # 'GET', 'POST', etc.

    # Always return Response:
    return Response({'key': 'value'})
    return Response(data, status=status.HTTP_201_CREATED)
```

## HTTP Method Handlers

```python
class MyView(APIView):
    def get(self, request):      # GET requests
    def post(self, request):     # POST requests
    def put(self, request):      # PUT requests
    def patch(self, request):    # PATCH requests
    def delete(self, request):   # DELETE requests
```

## Complete Example

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

class MultiModelDashboard(APIView):
    """
    Custom endpoint combining data from multiple models.
    This is where APIView shines!
    """
    def get(self, request):
        # Combine data from multiple models
        user = request.user
        stats = {
            'articles': Article.objects.filter(author=user).count(),
            'comments': Comment.objects.filter(author=user).count(),
            'likes': Like.objects.filter(user=user).count(),
        }
        return Response(stats)

# URL
urlpatterns = [
    path('dashboard/', MultiModelDashboard.as_view()),
]
```

## See Also

- **[viewsets.md](viewsets.md)** - Recommended for standard CRUD
- **[generic-views.md](generic-views.md)** - Single operation endpoints
