from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from .models import User, StudentInfo, StaffInfo, StudentProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','email','univ_id','first_name','middle_name','last_name','role','is_active']
        read_only_fields = ['id', 'email', 'univ_id', 'role', 'is_active']

class StudentInfoSerializer(serializers.ModelSerializer):
    user  = UserSerializer(read_only=True)
    class Meta:
        model = StudentInfo
        fields = ['user', 'course', 'year_level']

class StaffInfoSerializer(serializers.ModelSerializer):
    user  = UserSerializer(read_only=True)
    class Meta:
        model = StaffInfo
        fields = ['user', 'position']


class StudentProfileSerializer(serializers.ModelSerializer):
    """Full read-only view of a StudentProfile for the admin verification queue."""
    # Flatten the related user and student-info fields for the table
    first_name   = serializers.CharField(source='user.first_name', read_only=True)
    last_name    = serializers.CharField(source='user.last_name',  read_only=True)
    email        = serializers.EmailField(source='user.email',     read_only=True)
    univ_id      = serializers.CharField(source='user.univ_id',    read_only=True)
    course       = serializers.SerializerMethodField()
    year_level   = serializers.SerializerMethodField()
    id_image_url = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'first_name', 'last_name', 'email', 'univ_id',
            'course', 'year_level', 'id_image_url', 'verification_status',
            'verified_at',
        ]

    def get_course(self, obj):
        try:
            return obj.user.studentinfo.course
        except (AttributeError, ObjectDoesNotExist):
            return None

    def get_year_level(self, obj):
        try:
            return obj.user.studentinfo.year_level
        except (AttributeError, ObjectDoesNotExist):
            return None

    def get_id_image_url(self, obj):
        request = self.context.get('request')
        if obj.id_image and request:
            return request.build_absolute_uri(obj.id_image.url)
        return None


class StudentProfileVerifySerializer(serializers.Serializer):
    """Payload accepted by the verify/ action."""
    verification_status = serializers.ChoiceField(
        choices=['APPROVED', 'REJECTED']
    )
    verification_notes = serializers.CharField(
        required=False, allow_blank=True, default=''
    )

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    course = serializers.CharField(write_only=True, required=False, allow_blank=True)
    year_level = serializers.IntegerField(write_only=True, required=False)
    id_image = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'username', 'univ_id', 'course', 'year_level', 'id_image']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'username': {'required': False},
            'univ_id': {'required': False, 'allow_blank': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password')
        course = validated_data.pop('course', None)
        year_level = validated_data.pop('year_level', None)
        id_image = validated_data.pop('id_image', None)
        
        if validated_data.get('univ_id') == "":
            validated_data['univ_id'] = None
    
        if 'username' not in validated_data:
            import uuid
            base_username = validated_data['email'].split('@')[0]
            validated_data['username'] = f"{base_username}_{uuid.uuid4().hex[:8]}"
            
        validated_data['role'] = 'student'
            
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        if user.role == 'student':
            StudentInfo.objects.create(
                user=user,
                course=course or 'Not Specified',
                year_level=year_level or 1
            )
            StudentProfile.objects.create(
                user=user,
                id_image=id_image
            )
            
        return user
    
class StudentProfileAdminSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    univ_id = serializers.CharField(source='user.univ_id', read_only=True)
    
    course = serializers.CharField(source='user.studentinfo.course', read_only=True, default="N/A")
    year_level = serializers.IntegerField(source='user.studentinfo.year_level', read_only=True, default=0)
    id_image_url = serializers.SerializerMethodField()
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'first_name', 'last_name', 'email', 'univ_id', 'course', 'year_level',
            'id_image_url', 'verification_status', 'verification_notes', 'verified_at'
        ]
        read_only_fields = fields
    def get_id_image_url(self, obj):
        if obj.id_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.id_image.url)
        return None
        
class StudentVerificationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ['verification_status', 'verification_notes']
        
    def validate_verification_status(self, value):
        if value not in [StudentProfile.VerificationStatus.APPROVED, StudentProfile.VerificationStatus.REJECTED]:
            raise serializers.ValidationError("Status must be explicitly APPROVED or REJECTED.")
        return value
