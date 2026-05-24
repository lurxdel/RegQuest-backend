from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User

class MultiFieldAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in 
    using their Email, Username, or University ID.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
            
        try:
            user = User.objects.get(
                Q(email=username) | Q(username=username) | Q(univ_id=username)
            )
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None