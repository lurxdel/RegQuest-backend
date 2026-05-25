from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Request
from .serializers import RequestSerializer
from accounts.models import User
from _core.permissions import IsAdminOrStaff, IsAdminUser, CanCancelOwnPendingRequest, IsVerifiedIfStudent

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated]

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated, IsVerifiedIfStudent],
        'update': [IsAuthenticated, IsAdminOrStaff],
        'partial_update': [IsAuthenticated, IsAdminOrStaff],
        'destroy': [IsAuthenticated, IsAdminUser],
        'cancel': [CanCancelOwnPendingRequest],
    }

    def get_permissions(self):
        if hasattr(self, 'permission_classes_by_action') and self.action in self.permission_classes_by_action:
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Request.objects.none()

        if user.role == User.Roles.STUDENT:
            return Request.objects.filter(user=user)

        return Request.objects.all()


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='track/(?P<tracking_number>[^/.]+)', permission_classes=[AllowAny])
    def track(self, request, tracking_number=None):
        req = get_object_or_404(Request, tracking_number=tracking_number)
        serializer = self.get_serializer(req)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        req = self.get_object()
        req.status = Request.Status.CANCELLED
        req.save(update_fields=['status', 'updated_at'])
        return Response(
            {
            "message": "Request cancelled successfully", 
            "status": req.status
            }, 
            status=status.HTTP_200_OK
    )