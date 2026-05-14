from rest_framework import permissions
from accounts.models import User

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Roles.ADMIN
        )

class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Roles.STAFF
        )

class IsStudentUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Roles.STUDENT
        )

class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Roles.ADMIN, User.Roles.STAFF]
        )

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Admins also have access to all objects by default
        if request.user.role == User.Roles.ADMIN:
            return True
            
        return hasattr(obj, 'user') and obj.user == request.user

class CanCancelOwnPendingRequest(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Roles.ADMIN:
            return True
            
        is_owner = hasattr(obj, 'user') and obj.user == request.user
        is_pending = hasattr(obj, 'status') and obj.status == 'pending'
        
        return bool(is_owner and is_pending)
