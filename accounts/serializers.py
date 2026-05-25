from rest_framework import serializers
from .models import User, StudentInfo, StaffInfo, StudentProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','email','univ_id','first_name','middle_name','last_name','role']
        read_only_fields = ['id', 'email', 'univ_id', 'role']

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
