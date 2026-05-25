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

class IsVerifiedIfStudent(permissions.BasePermission):
    """
    If the user is a student, they must have an APPROVED verification_profile.
    Staff and Admins bypass this check.
    """
    # This automatically sends a 403 Forbidden with this exact detail message
    message = "Your account is pending verification. You cannot submit requests yet."
    
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        if user.role == User.Roles.STUDENT:
            # Check the reverse relation to the OneToOneField
            if hasattr(user, 'verification_profile'):
                return user.verification_profile.verification_status == 'APPROVED'
            return False
            
        # Admins and Staff bypass this check
        return True