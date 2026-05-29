from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone
from datetime import timedelta
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
            return Request.objects.filter(user=user).exclude(tracking_number__startswith='LEGACY-')
            
        if user.role == User.Roles.STAFF:
            return Request.objects.exclude(tracking_number__startswith='LEGACY-')

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

        def parse_docs(row):
            summary = row.get('document_summary')
            fallback = row.get('document_type__document_name')
            if summary:
                docs = []
                for line in summary.strip().split('\n'):
                    if ' x' in line:
                        docs.append(line.rsplit(' x', 1)[0].strip())
                    else:
                        docs.append(line.strip())
                return [d for d in docs if d]
            return [fallback] if fallback else []

        # Daily: last 7 days
        daily_start = now - timedelta(days=6)
        daily_qs = (
            Request.objects
            .filter(created_at__gte=daily_start)
            .annotate(day=TruncDate('created_at'))
            .values('id', 'day', 'document_type__document_name', 'document_summary')
        )
        daily_map = {}
        for row in daily_qs:
            day_str = row['day'].strftime('%a')
            if day_str not in daily_map:
                daily_map[day_str] = {}
            for doc_name in parse_docs(row):
                daily_map[day_str][doc_name] = daily_map[day_str].get(doc_name, 0) + 1

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
            .values('id', 'week', 'document_type__document_name', 'document_summary')
        )
        weekly_map = {}
        for row in weekly_qs:
            week_str = row['week'].strftime('%Y-%W')
            if week_str not in weekly_map:
                weekly_map[week_str] = {}
            for doc_name in parse_docs(row):
                weekly_map[week_str][doc_name] = weekly_map[week_str].get(doc_name, 0) + 1

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
        doc_type_qs = Request.objects.values('id', 'document_type__document_name', 'document_summary')
        
        distribution_map = {}
        total_document_types_requested = 0
        for row in doc_type_qs:
            for doc_name in parse_docs(row):
                distribution_map[doc_name] = distribution_map.get(doc_name, 0) + 1
                total_document_types_requested += 1

        doc_distribution = []
        for name, count in distribution_map.items():
            percentage = round((count / total_document_types_requested) * 100, 1) if total_document_types_requested else 0
            doc_distribution.append({
                'name': name,
                'count': count,
                'percentage': percentage,
            })
        doc_distribution.sort(key=lambda x: x['count'], reverse=True)

        # Staff performance
        staff_users = User.objects.filter(role__in=[User.Roles.STAFF, User.Roles.ADMIN])
        
        stats_qs = (
            Request.objects
            .filter(processed_by__in=staff_users)
            .values('processed_by')
            .annotate(
                completed=Count('id', filter=Q(status=Request.Status.COMPLETED)),
                pending=Count('id', filter=Q(status__in=[Request.Status.PENDING, Request.Status.PROCESSING])),
                avg_duration=Avg(F('processed_at') - F('created_at'), filter=Q(status=Request.Status.COMPLETED, processed_at__isnull=False))
            )
        )
        stats_map = {row['processed_by']: row for row in stats_qs}

        staff_performance = []
        for staff in staff_users:
            stats = stats_map.get(staff.id, {})
            completed = stats.get('completed', 0)
            pending = stats.get('pending', 0)
            avg_duration = stats.get('avg_duration')

            avg_days = None
            if avg_duration is not None:
                # avg_duration is a timedelta object on Python side
                avg_days = round(avg_duration.total_seconds() / 86400, 1)

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

    @action(detail=False, methods=['get'])
    def predict_insight(self, request):
        from .ml_service import get_weekly_prediction
        prediction = get_weekly_prediction(include_legacy=True)
        return Response(prediction)

    @action(detail=False, methods=['get'])
    def predict_insight_staff(self, request):
        from .ml_service import get_weekly_prediction
        prediction = get_weekly_prediction(include_legacy=False)
        return Response(prediction)