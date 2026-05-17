from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import User
from documents.models import Document
from .models import Request
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

# Create your tests here. 
class RBACTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', email='admin@test.com', password='pw', role=User.Roles.ADMIN)
        self.staff = User.objects.create_user(username='staff', email='staff@test.com', password='pw', role=User.Roles.STAFF)
        self.student1 = User.objects.create_user(username='student1', email='student1@test.com', password='pw', role=User.Roles.STUDENT)
        self.student2 = User.objects.create_user(username='student2', email='student2@test.com', password='pw', role=User.Roles.STUDENT)

        self.doc = Document.objects.create(document_name="Good Moral", description="Test doc", price=10.00, processing_time_days=3)

        self.req1 = Request.objects.create(user=self.student1, document_type=self.doc, quantity=1, total_price=100.00, est_release_date=timezone.now())
        self.req2 = Request.objects.create(user=self.student2, document_type=self.doc, quantity=1, total_price=100.00, est_release_date=timezone.now())

        self.request_list_url = '/api/v1/requests/'
        self.req1_url = f'/api/v1/requests/{self.req1.id}/'
        self.req2_url = f'/api/v1/requests/{self.req2.id}/'
    
    def authenticate_as(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_student_row_level_security(self):
        self.authenticate_as(self.student1)
        response = self.client.get(self.request_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(response.data[0]['id'], self.req1.id)

    def students_cannot_access_others_request(self):
        self.authenticate_as(self.student1)
        response = self.client.get(self. req2_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_view_all_requests(self):
        self.authenticate_as(self.staff)
        response = self.client.get(self.request_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_student_cannot_update_status(self):
        self.authenticate_as(self.student1)
        response = self.client.patch(self.req1_url, {'status': 'approved'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_cancel_own_pending_request(self):
        self.authenticate_as(self.student1)
        cancel_url = f'/api/v1/requests/{self.req1.id}/cancel/'
        
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.req1.refresh_from_db()
        self.assertEqual(self.req1.status, Request.Status.CANCELLED)

    def test_student_cannot_cancel_others_request(self):
        self.authenticate_as(self.student1)
        cancel_url = f'/api/v1/requests/{self.req2.id}/cancel/' 
        
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
