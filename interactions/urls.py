from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InviteViewSet,
    MatchViewSet,
    ProfileViewViewSet,
    ReactionViewSet,
)

router = DefaultRouter()
router.register('reactions', ReactionViewSet, basename='reaction')
router.register('views', ProfileViewViewSet, basename='view')
router.register('matches', MatchViewSet, basename='match')
router.register('invites', InviteViewSet, basename='invite')

urlpatterns = [
    path('', include(router.urls)),
]
