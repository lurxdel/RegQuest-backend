from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone
from datetime import timedelta
from .models import Request
from .serializers import RequestSerializer
from accounts.models import User
from _core.permissions import IsAdminOrStaff, IsAdminUser, CanCancelOwnPendingRequest

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated]

    permission_classes_by_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'create': [IsAuthenticated],
        'update': [IsAuthenticated, IsAdminOrStaff],
        'partial_update': [IsAuthenticated, IsAdminOrStaff],
        'destroy': [IsAuthenticated, IsAdminUser],
        'cancel': [CanCancelOwnPendingRequest],
        'dashboard': [IsAdminOrStaff],
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

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        now = timezone.now()

        # Daily: last 7 days
        daily_start = now - timedelta(days=6)
        daily_qs = (
            Request.objects
            .filter(created_at__gte=daily_start)
            .annotate(day=TruncDate('created_at'))
            .values('day', 'document_type__document_name')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        daily_map = {}
        for row in daily_qs:
            day_str = row['day'].strftime('%a')
            if day_str not in daily_map:
                daily_map[day_str] = {}
            daily_map[day_str][row['document_type__document_name']] = row['count']

        daily_data = []
        for i in range(6, -1, -1):
            d = now - timedelta(days=i)
            label = d.strftime('%a')
            daily_data.append({
                'label': label,
                'date': d.strftime('%Y-%m-%d'),
                'breakdown': daily_map.get(label, {}),
                'total': sum(daily_map.get(label, {}).values()),
            })

        # Weekly: last 7 weeks
        weekly_start = now - timedelta(weeks=6)
        weekly_qs = (
            Request.objects
            .filter(created_at__gte=weekly_start)
            .annotate(week=TruncWeek('created_at'))
            .values('week', 'document_type__document_name')
            .annotate(count=Count('id'))
            .order_by('week')
        )
        weekly_map = {}
        for row in weekly_qs:
            week_str = row['week'].strftime('%Y-%W')
            if week_str not in weekly_map:
                weekly_map[week_str] = {}
            weekly_map[week_str][row['document_type__document_name']] = row['count']

        weekly_data = []
        for i in range(6, -1, -1):
            w = now - timedelta(weeks=i)
            week_str = w.strftime('%Y-%W')
            weekly_data.append({
                'label': f'Week {7 - i}',
                'week': week_str,
                'breakdown': weekly_map.get(week_str, {}),
                'total': sum(weekly_map.get(week_str, {}).values()),
            })

        # Document type distribution
        total_requests = Request.objects.count()
        doc_type_qs = (
            Request.objects
            .values('document_type__document_name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        doc_distribution = [
            {
                'name': row['document_type__document_name'],
                'count': row['count'],
                'percentage': round(row['count'] / total_requests * 100, 1) if total_requests else 0,
            }
            for row in doc_type_qs
        ]

        # Staff performance
        staff_users = User.objects.filter(role__in=[User.Roles.STAFF, User.Roles.ADMIN])
        staff_performance = []
        for staff in staff_users:
            completed = Request.objects.filter(processed_by=staff, status=Request.Status.COMPLETED).count()
            pending = Request.objects.filter(
                processed_by=staff, status__in=[Request.Status.PENDING, Request.Status.PROCESSING]
            ).count()
            completed_qs = Request.objects.filter(
                processed_by=staff, status=Request.Status.COMPLETED, processed_at__isnull=False
            )
            avg_days = None
            if completed_qs.exists():
                durations = [(r.processed_at - r.created_at).total_seconds() / 86400 for r in completed_qs]
                avg_days = round(sum(durations) / len(durations), 1)
            staff_performance.append({
                'id': staff.id,
                'name': f'{staff.first_name} {staff.last_name}'.strip() or staff.username,
                'username': staff.username,
                'role': staff.role,
                'completed': completed,
                'pending': pending,
                'avg_days': avg_days,
            })
        staff_performance.sort(key=lambda x: x['completed'], reverse=True)

        return Response({
            'request_volume': {'daily': daily_data, 'weekly': weekly_data},
            'document_type_distribution': doc_distribution,
            'staff_performance': staff_performance,
            'meta': {'total_requests': total_requests, 'generated_at': now.isoformat()},
        })