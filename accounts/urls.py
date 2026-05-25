from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, StudentInfoViewSet, StaffInfoViewSet, RegisterView, StudentProfileViewSet, admin_demo, staff_demo, student_demo, logout_view, login

router = DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'studentinfo', StudentInfoViewSet)
router.register(r'staffinfo', StaffInfoViewSet)
router.register(r'verifications', StudentProfileViewSet, basename='verification')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', login, name='login'),
    path('logout/', logout_view, name='logout'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    #demo routes(for testing only)
    path('demo/admin/', admin_demo, name='demo_admin'),
    path('demo/staff/', staff_demo, name='demo_staff'),
    path('demo/student/', student_demo, name='demo_student'),
]
