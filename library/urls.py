from django.urls import include, path
from rest_framework.routers import DefaultRouter

from library.views import (
    AuthorViewSet,
    BookCopyViewSet,
    BookViewSet,
    GenreViewSet,
    LoanIssueAPIView,
    LoanReturnAPIView,
    LoanViewSet,
)

app_name = "library"

catalog_router = DefaultRouter()
catalog_router.register("authors", AuthorViewSet, basename="authors")
catalog_router.register("genres", GenreViewSet, basename="genres")
catalog_router.register("books", BookViewSet, basename="books")
catalog_router.register("book-copies", BookCopyViewSet, basename="book-copies")

loan_router = DefaultRouter()
loan_router.register("", LoanViewSet, basename="loan")

urlpatterns = [
    path("catalog/", include(catalog_router.urls)),
    path("loans/issue/", LoanIssueAPIView.as_view(), name="loan-issue"),
    path("loans/return/", LoanReturnAPIView.as_view(), name="loan-return"),
    path("loans/", include(loan_router.urls)),
]
