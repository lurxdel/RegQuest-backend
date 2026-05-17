from django.contrib.auth import authenticate
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, StudentInfo, StaffInfo
from .serializers import UserSerializer, StudentInfoSerializer, StaffInfoSerializer, RegisterSerializer

from _core.permissions import IsAdminUser, IsStaffUser, IsStudentUser

#demo endpoints (for frontend testing only)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_demo(request):
    return Response({"message": "Hello Admin! You have full access."})
@api_view(['GET'])
@permission_classes([IsStaffUser])
def staff_demo(request):
    return Response({"message": "Hello Staff! You can manage requests."})
@api_view(['GET'])
@permission_classes([IsStudentUser])
def student_demo(request):
    return Response({"message": "Hello Student! You can view your own data."})

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


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
            
        if user.role == User.Roles.STUDENT:
            return User.objects.filter(id=user.id)
            
        return User.objects.all()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_role(self, request, pk=None):
        user_to_modify = self.get_object()
        new_role = request.data.get('role')

        if new_role not in dict(User.Roles.choices):
            return Response(
                {"error": f"Invalid role. Choices are: {list(dict(User.Roles.choices).keys())}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_to_modify.role = new_role
        user_to_modify.save(update_fields=['role'])
        
        return Response({
            "message": "Role updated successfully",
            "user_id": user_to_modify.id,
            "new_role": new_role
        })


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