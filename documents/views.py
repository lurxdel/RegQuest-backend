from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Document
from .serializers import DocumentSerializer
from _core.permissions import IsAdminOrStaff

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    
    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated, IsAdminOrStaff],
        'update': [IsAuthenticated, IsAdminOrStaff],
        'partial_update': [IsAuthenticated, IsAdminOrStaff],
        'destroy': [IsAuthenticated, IsAdminOrStaff],
    }   

    def get_permissions(self):
        if hasattr(self, 'permission_classes_by_action') and self.action in self.permission_classes_by_action:
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        return super().get_permissions()