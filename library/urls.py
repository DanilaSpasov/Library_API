from django.urls import include, path
from rest_framework.routers import DefaultRouter

from library.views import (
    AuthorViewSet,
    AvailabilitySubscriptionViewSet,
    BookCopyViewSet,
    BookViewSet,
    GenreViewSet,
    LoanIssueAPIView,
    LoanReturnAPIView,
    LoanViewSet,
)

app_name = "library"

router = DefaultRouter()
router.register("catalog/authors", AuthorViewSet, basename="authors")
router.register("catalog/genres", GenreViewSet, basename="genres")
router.register("catalog/books", BookViewSet, basename="books")
router.register("catalog/book-copies", BookCopyViewSet, basename="book-copies")
router.register("loans", LoanViewSet, basename="loan")
router.register(
    "subscriptions",
    AvailabilitySubscriptionViewSet,
    basename="subscription",
)

urlpatterns = [
    path("loans/issue/", LoanIssueAPIView.as_view(), name="loan-issue"),
    path("loans/return/", LoanReturnAPIView.as_view(), name="loan-return"),
    path("", include(router.urls)),
]
