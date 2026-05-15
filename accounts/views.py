from django.contrib.auth import authenticate
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, StudentInfo, StaffInfo
from .serializers import (
    UserSerializer,
    StudentInfoSerializer,
    StaffInfoSerializer,
    RegisterSerializer
)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


from rest_framework.decorators import api_view, permission_classes
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(username=email, password=password)

    if user is None:
        return Response(
            {"message": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"message": "Account is inactive"},
            status=status.HTTP_403_FORBIDDEN
        )

    refresh = RefreshToken.for_user(user)

    user_data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "univ_id": user.univ_id
    }

    if user.role == 'student':
        try:
            student_info = StudentInfo.objects.get(user=user)
            user_data["course"] = student_info.course
            user_data["year_level"] = student_info.year_level
        except StudentInfo.DoesNotExist:
            pass

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": user_data
    })


# VIEWSETS
class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
            
        if user.role == User.Roles.STUDENT:
            return User.objects.filter(id=user.id)
            
        return User.objects.all()


class StudentInfoViewSet(viewsets.ModelViewSet):
    queryset = StudentInfo.objects.all()
    serializer_class = StudentInfoSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return StudentInfo.objects.none()
            
        if user.role == User.Roles.STUDENT:
            return StudentInfo.objects.filter(user=user)
        return StudentInfo.objects.all()


class StaffInfoViewSet(viewsets.ModelViewSet):
    queryset = StaffInfo.objects.all()
    serializer_class = StaffInfoSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return StaffInfo.objects.none()
            
        if user.role == User.Roles.STUDENT:
            return StaffInfo.objects.none()
            
        return StaffInfo.objects.all()