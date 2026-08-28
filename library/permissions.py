from rest_framework.permissions import BasePermission

from users.models import ROLE_ADMIN, ROLE_LIBRARIAN, ROLE_READER


class IsReader(BasePermission):
    """Разрешает действие только читателю."""

    message = "Действие доступно только читателю."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == ROLE_READER


class IsLibrarianOrAdmin(BasePermission):
    """Разрешает действие библиотекарю и администратору."""

    message = "Действие доступно только библиотекарю или администратору."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            ROLE_LIBRARIAN,
            ROLE_ADMIN,
        )


class IsCatalogManager(BasePermission):
    """Разрешает изменение каталога библиотекарю и администратору."""

    message = "Изменять каталог может только библиотекарь или администратор."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            ROLE_LIBRARIAN,
            ROLE_ADMIN,
        )


class IsAdminRole(BasePermission):
    """Разрешает действие только администратору."""

    message = "Это действие доступно только администратору."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == ROLE_ADMIN
