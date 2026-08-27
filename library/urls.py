from django.urls import include, path
from rest_framework.routers import DefaultRouter

from library.views import AuthorViewSet, BookCopyViewSet, BookViewSet, GenreViewSet

app_name = "library"

router = DefaultRouter()
router.register("authors", AuthorViewSet, basename="authors")
router.register("genres", GenreViewSet, basename="genres")
router.register("books", BookViewSet, basename="books")
router.register("book-copies", BookCopyViewSet, basename="book-copies")

urlpatterns = [
    path("", include(router.urls)),
]
