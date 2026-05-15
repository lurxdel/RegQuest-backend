from rest_framework import permissions
from accounts.models import User

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Roles.ADMIN)

class IsStaffUser(permissions.BasePermission):
    """
    Allows access only to staff users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Roles.STAFF)

class IsStudentUser(permissions.BasePermission):
    """
    Allows access only to student users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Roles.STUDENT)

class IsAdminOrStaff(permissions.BasePermission):
    """
    Allows access to admin or staff users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in [User.Roles.ADMIN, User.Roles.STAFF])
        )

class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to access it.
    Assumes the model instance has a `user` attribute.
    """
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and hasattr(obj, 'user') and obj.user == request.user)

class CanCancelOwnPendingRequest(permissions.BasePermission):
    """
    Allows students to cancel their own requests ONLY if they are pending.
    """
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            hasattr(obj, 'user') and obj.user == request.user and 
            hasattr(obj, 'status') and obj.status == "pending"
        )
