import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds an initial admin account for production deployment.'

    def handle(self, *args, **options):
        email = os.environ.get('INITIAL_ADMIN_EMAIL')
        username = os.environ.get('INITIAL_ADMIN_USERNAME')
        password = os.environ.get('INITIAL_ADMIN_PASSWORD')

        if not all([email, username, password]):
            self.stdout.write(
                self.style.WARNING("Skipping admin seed: Missing environment variables "
                                   "(INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_PASSWORD).")
            )
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(f"Admin account for {email} already exists. Skipping."))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"A user with username {username} already exists. Skipping."))
            return

        try:
            User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
                role=User.Roles.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully seeded admin account: {email}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to seed admin account: {str(e)}"))
