from django.contrib.auth import authenticate
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, StudentInfo, StaffInfo
from .serializers import UserSerializer, StudentInfoSerializer, StaffInfoSerializer, RegisterSerializer

from _core.permissions import IsAdminUser, IsStaffUser, IsStudentUser

from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import StudentProfile
from .serializers import StudentProfileAdminSerializer, StudentVerificationDecisionSerializer

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

class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

from rest_framework.parsers import MultiPartParser, FormParser

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"message": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

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

    if user.role == User.Roles.STUDENT:
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {"message": "Successfully logged out"}, 
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": "Invalid or expired token"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

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
    http_method_names = ['get', 'patch', 'head', 'options']

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
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return StaffInfo.objects.none()
            
        if user.role == User.Roles.STUDENT:
            return StaffInfo.objects.none()
            
        return StaffInfo.objects.all()

class VerificationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
class StudentProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only ViewSet. 
    ReadOnlyModelViewSet prevents native POST/PUT/PATCH/DELETE.
    Modifications only allowed via the explicit secure `verify` action.
    """
    # Use select_related to optimize DB queries when fetching the joined user and academic info
    queryset = StudentProfile.objects.all().select_related('user', 'user__studentinfo').order_by('-user__created_at')
    permission_classes = [IsAdminUser] # SECURITY: Admin ONLY. Staff blocked.
    pagination_class = VerificationPagination
    def get_serializer_class(self):
        # Dynamically route to the strict decision serializer when verifying
        if self.action == 'verify':
            return StudentVerificationDecisionSerializer
        return StudentProfileAdminSerializer
    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status', None)
        search_param = self.request.query_params.get('search', None)
        if status_param:
            queryset = queryset.filter(verification_status=status_param.upper())
        
        if search_param:
            # Future-proof search across multiple joined fields
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_param) |
                Q(user__last_name__icontains=search_param) |
                Q(user__email__icontains=search_param) |
                Q(user__univ_id__icontains=search_param)
            )
        return queryset
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            # SECURITY: Force verified_by and verified_at server-side.
            # Even if an attacker sent 'verified_by' in the JSON, the serializer 
            # drops it, and we explicitly override it here using the authenticated token.
            serializer.save(
                verified_by=request.user,
                verified_at=timezone.now()
            )
            return Response(
                {"message": f"Profile updated successfully."}, 
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)