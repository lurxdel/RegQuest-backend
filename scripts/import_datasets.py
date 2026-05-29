import os
import django
import sys
import pandas as pd
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Setup Django
sys.path.append(r"C:\xampp\htdocs\RegQuest-backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_core.settings")
django.setup()

from credential_requests.models import Request
from documents.models import Document
from accounts.models import User

# Get a dummy user for legacy data
student, _ = User.objects.get_or_create(
    username='legacy_student', 
    defaults={
        'email': 'legacy@example.com', 
        'role': 'student',
        'first_name': 'Legacy',
        'last_name': 'Import'
    }
)

# Map codes from dataset to your DocumentType names
doc_map = {
    '1': 'Transcript of Records',
    '2': 'Honorable Dismissal',
    '3': 'CAV',
    '4': 'Certification',
    '5': 'Evaluation',
    '6': 'Form 137',
    '7': 'Diploma Replacement',
    '8': 'World Education Services',
    '9': 'Permit to Study',
    '10': 'Verification',
    '4a': 'Officially Enrolled',
    '4b': 'GPA',
    '4c': 'Graduated',
    '4d': 'Earned Units',
    '4e': 'Subjects Enrolled',
    '4f': 'CAR',
    '4g': 'Subjects w/ grades',
    '4h': 'USTP conversion',
    '4i': 'English Medium',
    '4j': 'Grading System',
    '4k': 'Cum Laude',
    '4l': 'Graduating'
}

# Ensure all Document models exist
db_docs = {}
for code, name in doc_map.items():
    doc, _ = Document.objects.get_or_create(
        document_name=name,
        defaults={'description': 'Legacy imported', 'price': 0, 'processing_time_days': 3}
    )
    db_docs[code] = doc

folder = r"C:\xampp\htdocs\RegQuest-backend\datasets"
files = [f for f in os.listdir(folder) if f.endswith('.xlsx') or f.endswith('.xlsm')]
imported_count = 0
skipped_count = 0

print("Cleaning and importing datasets. Please wait...")

# Disconnect WebSocket signal temporarily to prevent mass broadcast crashes during bulk import
from django.db.models.signals import post_save
from credential_requests.models import broadcast_request_update
try:
    post_save.disconnect(broadcast_request_update, sender=Request)
except Exception:
    pass

for file in files:
    print(f"Processing {file}...")
    try:
        df = pd.read_excel(os.path.join(folder, file), header=None, engine='openpyxl')
    except Exception as e:
        print(f"  Error reading {file}: {e}")
        continue
    
    # Find the header row (look for 'No.' in the first column)
    header_idx = -1
    for i, row in df.iterrows():
        if str(row[0]).strip() == 'No.':
            header_idx = i
            break
            
    if header_idx == -1:
        print(f"  Skipping {file}: Could not find header row.")
        continue
        
    for i in range(header_idx + 1, len(df)):
        row = df.iloc[i]
        date_requested = row[6]
        credential_code = str(row[4]).strip().lower()
        purpose_raw = str(row[5])
        
        if pd.isna(date_requested) or credential_code == 'nan' or credential_code == 'None':
            skipped_count += 1
            continue
            
        try:
            if isinstance(date_requested, str):
                parsed_date = pd.to_datetime(date_requested).to_pydatetime()
            else:
                parsed_date = date_requested
        except Exception:
            skipped_count += 1
            continue
            
        if credential_code in doc_map:
            doc_model = db_docs[credential_code]
            
            # Simulate ML training data for release dates since Excel columns were empty
            import random
            base_days = doc_model.processing_time_days if doc_model.processing_time_days else 3
            # Add some noise for realism (-1 to +2 days)
            simulated_days = max(1, base_days + random.randint(-1, 2))
            simulated_release_date = parsed_date + timedelta(days=simulated_days)
            
            req = Request.objects.create(
                user=student,
                document_type=doc_model,
                quantity=1,
                total_price=0,
                status='completed',
                tracking_number=f"LEGACY-{imported_count}-{os.urandom(4).hex()}",
                document_summary=doc_model.document_name + " x1",
                processed_at=simulated_release_date,
                est_release_date=simulated_release_date
            )
            # Update created_at safely overriding auto_now_add
            Request.objects.filter(id=req.id).update(created_at=parsed_date)
            imported_count += 1
        else:
            skipped_count += 1
            
print(f"Successfully imported {imported_count} legacy requests!")
print(f"Skipped {skipped_count} invalid/empty rows.")
