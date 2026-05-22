from rest_framework import serializers
from .models import Request
from accounts.models import User

class RequestSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    document_name = serializers.CharField(source='document_type.document_name', read_only=True)
    processing_time_days = serializers.IntegerField(source='document_type.processing_time_days', read_only=True)
    class Meta:
        model = Request
        fields = '__all__'
        read_only_fields = ['user','tracking_number', 'created_at', 'updated_at',]
    def get_student_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
        
    def validate(self, attrs):
        request = self.context.get('request')

        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.role == User.Roles.STUDENT:
                restricted_fields = ['status','processed_by', 'processed_at', 'est_release_date']
                
                for field in restricted_fields:
                    if field in attrs:
                        raise serializers.ValidationError({field: "You do not have permission to modify this field."})

        return super().validate(attrs)

        