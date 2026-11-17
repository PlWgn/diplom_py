from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import HobbyViewSet, PhotoViewSet, RegisterView, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('photos', PhotoViewSet, basename='photo')
router.register('hobbies', HobbyViewSet, basename='hobby')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path(
        'auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'
    ),
    path('', include(router.urls)),
]
