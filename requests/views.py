from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .models import Request
from .serializers import RequestSerializer
from accounts.models import User

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated]

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