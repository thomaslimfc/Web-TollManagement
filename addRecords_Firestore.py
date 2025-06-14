import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
cred = credentials.Certificate("plus-370c3-firebase-adminsdk-v6bx7-1c1c536c62.json")
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

# Add multiple records in a batch
def add_records_in_batch(collection_name, records):
    batch = db.batch()
    for record in records:
        doc_ref = db.collection(collection_name).document()  # Auto-generate ID
        batch.set(doc_ref, record)
    try:
        batch.commit()
        print("Batch write successful")
    except Exception as e:
        print(f"Error in batch write: {e}")

# Example usage
positions = [
    {"positionId": "PID00002", "positionName": "system administator"},
    {"positionId": "PID00003", "positionName": "traffic management officer"},
    {"positionId": "PID00004", "positionName": "maintenance staff"},
    {"positionId": "PID00005", "positionName": "customer support representative"},
    {"positionId": "PID00006", "positionName": "manager"}
]

add_records_in_batch("position", positions)