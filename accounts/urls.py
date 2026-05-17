from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet, StudentInfoViewSet, StaffInfoViewSet, RegisterView, admin_demo, staff_demo, student_demo

router = DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'studentinfo', StudentInfoViewSet)
router.register(r'staffinfo', StaffInfoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    #demo routes(for testing only)
    path('demo/admin/', admin_demo, name='demo_admin'),
    path('demo/staff/', staff_demo, name='demo_staff'),
    path('demo/student/', student_demo, name='demo_student'),
]
