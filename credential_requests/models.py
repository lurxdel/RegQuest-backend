from django.db import models
from django.conf import settings
from documents.models import Document
from django.utils import timezone
from datetime import timedelta
import uuid

# Create your models here.
class Request(models.Model):
    tracking_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    document_type = models.ForeignKey(Document, on_delete=models.PROTECT)
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    document_summary = models.TextField(blank=True, null=True, help_text="Summary of all documents requested and their copies")
    est_release_date = models.DateTimeField(
        null=True,
        blank=True
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='processed_requests'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.tracking_number:
            self.tracking_number = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        if not self.est_release_date:
            self.est_release_date = (
                timezone.now() + timedelta(days=5)
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.document_type.document_name + " request by " + self.user.username

from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=Request)
def broadcast_request_update(sender, instance, **kwargs):
    from .serializers import RequestSerializer
    channel_layer = get_channel_layer()
    serializer = RequestSerializer(instance)
    async_to_sync(channel_layer.group_send)(
        'requests_updates',
        {
            'type': 'request_message',
            'message': serializer.data
        }
    )