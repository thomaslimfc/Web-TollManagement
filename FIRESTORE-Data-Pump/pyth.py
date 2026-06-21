import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from paddleocr import PaddleOCR
from collections import defaultdict, Counter
import re
import time
import os
import csv
import threading
import queue
from datetime import datetime
from difflib import SequenceMatcher
import traceback

# Import Firebase and Google Cloud Storage tools
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage
import google.auth.exceptions

# --- System global variables ---
SELECTED_LOCATION_ID = "TLID00001"
SELECTED_LOCATION_DESC = "Penang Bridge"
SELECTED_TOLL_TYPE = "Open"  # Toll type: can be Open or Closed
FORCE_MODE = "ENTER_ONLY"
IS_SHUTTING_DOWN = False

# Get the folder path where this script is saved
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(SCRIPT_DIR, "serviceAccountKey.json")

# Connect to Firebase database and cloud storage
try:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': "plus-370c3.appspot.com",
        'httpTimeout': 30,
        'connectTimeout': 15
    })
    db = firestore.client()
    bucket = storage.bucket()
    print("[FIREBASE SUCCESS] Connected successfully to security credential endpoint & storage bucket.")
except Exception as e:
    print(f"[FIREBASE INITIALIZATION ERROR] Check configurations or network paths: {e}")
    exit(1)

# =========================================================================
# Get toll locations from the database
# =========================================================================
print("\n===========================================================")
print(  "          PLUS HIGHWAYS LPR TOLL COLLECTION SYSTEM         ")
print(  "===========================================================")

print("[SYSTEM] Fetching operational toll locations from Firestore...")
try:
    locations_ref = db.collection("tollLocation").get()
    location_map = {}

    if not locations_ref:
        print("[DATABASE ERROR] No locations found in 'tollLocation'. Falling back to defaults.")
        location_map['1'] = ("TLID00001", "Penang Bridge (Fallback)", "Open")
    else:
        sorted_docs = sorted(locations_ref, key=lambda d: d.id)
        for idx, doc in enumerate(sorted_docs, start=1):
            data = doc.to_dict()
            loc_id = data.get("tollLocationID", doc.id)
            desc = data.get("description", "Unknown Location")
            t_type = data.get("tollType", "Closed")
            location_map[str(idx)] = (loc_id, desc, t_type)
except Exception as e:
    print(f"[DATABASE ERROR] Failed to fetch locations: {e}")
    location_map['1'] = ("TLID00001", "Penang Bridge (Backup)", "Open")

print("\nSelect Current Toll Location Plaza:")
for key, (loc_id, desc, t_type) in location_map.items():
    print(f"{key}. {desc} ({loc_id}) [Type: {t_type}]")
print("-------------------------------------------------------")

while True:
    loc_choice = input("Enter choice number: ").strip()
    if loc_choice in location_map:
        SELECTED_LOCATION_ID, SELECTED_LOCATION_DESC, SELECTED_TOLL_TYPE = location_map[loc_choice]
        print(f"\n[LOCATION ACTIVE] Confirmed Plaza: >>> {SELECTED_LOCATION_DESC} ({SELECTED_LOCATION_ID}) <<<")
        break
    else:
        print("Invalid selection.")

# Ask for entry or exit gate only if the toll type is Closed
if SELECTED_TOLL_TYPE.strip().capitalize() == "Closed":
    print("\nSelect Operational Mode for this Toll Booth Session:")
    print("1. Entry Gate (Logs vehicle entry only / Supports single booth initialization)")
    print("2. Exit Gate (Finds pending entry, calculates tariff, and deducts balance)")
    print("-------------------------------------------------------")

    while True:
        user_choice = input("Enter choice (1 or 2): ").strip()
        if user_choice == '1':
            FORCE_MODE = "ENTER_ONLY"
            print("\n[GATE CONFIG] Configured as: >>> CLOSED TOLL - ENTRY BOOTH <<<")
            break
        elif user_choice == '2':
            FORCE_MODE = "EXIT_ONLY"
            print("\n[GATE CONFIG] Configured as: >>> CLOSED TOLL - EXIT BOOTH <<<")
            break
        else:
            print("Invalid choice. Type 1 or 2.")
else:
    FORCE_MODE = "ENTRY_EQUAL_EXIT"
    print("\n[GATE CONFIG] Configured as: >>> OPEN TOLL - ENTRY = EXIT SINGLE POINT BOOTH <<<")

CURRENT_BOOTH_ID = "BID00004"

# Create a folder to save output images
os.makedirs("output/annotated_results", exist_ok=True)

# Load AI models for detection, tracking, and text reading
model = YOLO("licensePlateDetector.pt").to('cuda')
tracker = DeepSort(max_age=30)
ocr_model = PaddleOCR(use_angle_cls=False, lang='en', show_log=False, use_gpu=True)

# Shared memory variables
ocr_queue = queue.Queue(maxsize=10)
plate_text_final = dict()
plate_to_ids = defaultdict(set)
track_plate_candidates = defaultdict(list)
active_tracks = set()
processed_tracks = set()

recent_passages = {}
PASSAGE_WINDOW = 30

data_lock = threading.Lock()
db_write_lock = threading.Lock()
csv_file_lock = threading.Lock()

COMMON_SUBSTITUTIONS = {
    'N': 'W', 'M': 'W', 'H': 'W', 'I': 'J',
    '1': 'I', '0': 'O', '8': 'B', 'B': '8'
}


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def normalize_plate(text):
    text = text.upper().strip()
    if len(text) >= 2:
        first = text[0]
        if first in COMMON_SUBSTITUTIONS:
            text = COMMON_SUBSTITUTIONS[first] + text[1:]
    return text


def valid_plate(text):
    pattern = r'^[A-Z]{1,3}[0-9]{1,4}[A-Z]{0,2}$'
    if not re.match(pattern, text) or len(text) < 5:
        return False
    return True


def get_sequential_id(collection_name, prefix):
    with db_write_lock:
        try:
            records_ref = db.collection(collection_name)
            all_docs = records_ref.get()
            if not all_docs:
                return f"{prefix}00001"

            max_num = 0
            for doc in all_docs:
                doc_id = doc.id
                if doc_id.startswith(prefix):
                    try:
                        num_part = int(doc_id.replace(prefix, ""))
                        if num_part > max_num:
                            max_num = num_part
                    except ValueError:
                        continue

            return f"{prefix}{max_num + 1:05d}"
        except Exception:
            return f"{prefix}00001"


def append_to_backup_csv(plate_text, track_id):
    with csv_file_lock:
        file_path = 'realtime_lpr_results.csv'
        file_exists = os.path.isfile(file_path)
        try:
            with open(file_path, mode='a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(['Timestamp', 'Plate Text', 'Track ID', 'Location', 'Mode'])
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    plate_text,
                    track_id,
                    SELECTED_LOCATION_DESC,
                    FORCE_MODE
                ])
        except Exception as e:
            print(f"[LOCAL CSV BACKUP ERROR] Could not save verification entry to local disk: {e}")


def upload_crop_in_memory(plate_crop, track_id):
    if plate_crop is None or plate_crop.size == 0:
        return ""
    try:
        success, encoded_image = cv2.imencode('.png', plate_crop)
        if not success:
            return ""

        blob_bytes = encoded_image.tobytes()
        blob_path = f"lpr_crops/{datetime.utcnow().strftime('%Y%m%d')}/track_{track_id}_{int(time.time())}.png"

        blob = bucket.blob(blob_path)
        blob.upload_from_string(blob_bytes, content_type='image/png')
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"[CLOUD STORAGE ERROR] Skipped image asset transfer sync: {e}")
        return ""


def create_lpr_record(winner, confidence, vehicle_id, track_id, event_type, plate_crop):
    try:
        lpr_id = get_sequential_id("lprRecord", "LRID")
        cloud_url = upload_crop_in_memory(plate_crop, track_id)

        db.collection("lprRecord").document(lpr_id).set({
            "lprRecordID": lpr_id,
            "vehicleID": vehicle_id,
            "licensePlate": winner,
            "confidenceScore": float(f"{confidence:.2f}"),
            "capturedAt": datetime.utcnow(),
            "tollLocationID": SELECTED_LOCATION_ID,
            "tollBoothID": CURRENT_BOOTH_ID,
            "tollEventType": event_type,
            "cropImageURL": cloud_url
        })
        print(f"[FIRESTORE LPR] AUDIT SAVED: Capture entry {lpr_id} generated for {winner}.")
        return lpr_id
    except Exception as e:
        print(f"[LPR LOGGING CRASH] Audit tracking lost: {e}")
        return None


def process_exit_billing(transaction_doc_ref, entry_time, entry_location_id, current_exit_lpr_id, winner, vehicle_id, vehicle_type_id, commuter_id, now):
    """Calculates route fees, updates customer balances, and saves transaction status."""
    try:
        time_delta = now - entry_time.replace(tzinfo=None)
        travel_duration = round(time_delta.total_seconds() / 3600.0, 4)

        # Step 1: Look for the fee in the database using filters
        tariff_query = db.collection("tollTariff") \
            .where("entryTollLocationID", "==", entry_location_id) \
            .where("exitTollLocationID", "==", SELECTED_LOCATION_ID) \
            .where("vehicleTypeID", "==", vehicle_type_id) \
            .limit(1).get()

        tariff_match = None
        if tariff_query:
            tariff_match = tariff_query[0].to_dict()
            tariff_id = tariff_query[0].id
        else:
            # Step 2: Search all data if the database index is not ready
            print(f"[SYSTEM NOTICE] Index lookup empty. Initiating data-stream safety scan...")
            all_tariffs = db.collection("tollTariff").get()
            for t_doc in all_tariffs:
                td = t_doc.to_dict()
                if str(td.get("entryTollLocationID")).strip() == str(entry_location_id).strip() and \
                   str(td.get("exitTollLocationID")).strip() == str(SELECTED_LOCATION_ID).strip() and \
                   str(td.get("vehicleTypeID")).strip() == str(vehicle_type_id).strip():
                    tariff_match = td
                    tariff_id = t_doc.id
                    break

        if not tariff_match:
            print(f"[TARIFF ERROR] Route mapping missing from '{entry_location_id}' to exit '{SELECTED_LOCATION_ID}' for {vehicle_type_id}.")
            transaction_doc_ref.update({
                "status": "TariffNotFound",
                "createdAt": now,
                "balanceBefore": None,
                "balanceAfter": None
            })
            return False

        tariff_rate = float(tariff_match.get("tariffRate"))

        commuter_doc_ref = db.collection("commuter").document(commuter_id)
        commuter_snap = commuter_doc_ref.get()

        if not commuter_snap.exists:
            commuter_query = db.collection("commuter").where("commuterID", "==", commuter_id).limit(1).get()
            if not commuter_query:
                print(f"[ACCOUNT ERROR] Commuter profile reference mapping {commuter_id} does not exist.")
                transaction_doc_ref.update({
                    "status": "VehicleNotRegistered",
                    "createdAt": now,
                    "balanceBefore": None,
                    "balanceAfter": None
                })
                return False
            commuter_doc_ref = commuter_query[0].reference
            commuter_data = commuter_query[0].to_dict()
        else:
            commuter_data = commuter_snap.to_dict()

        balance_before = float(commuter_data.get("balance", 0.0))

        if balance_before < tariff_rate:
            print(f"[WALLET REJECTED] Insufficient Funds for {commuter_id}. Required: RM{tariff_rate:.2f}")
            transaction_doc_ref.update({
                "exitLprRecordID": current_exit_lpr_id,
                "travelDuration": travel_duration,
                "tollTariffID": tariff_id,
                "tariffRate": tariff_rate,
                "balanceBefore": balance_before,
                "balanceAfter": balance_before,
                "status": "InsufficientBalance",
                "createdAt": now
            })
            return False

        balance_after = round(balance_before - tariff_rate, 2)
        commuter_doc_ref.update({"balance": balance_after})
        print(f"[WALLET TRANSACTION] DEBITED: {commuter_data.get('fullName')}. RM {balance_before:.2f} -> RM {balance_after:.2f}")

        transaction_doc_ref.update({
            "exitLprRecordID": current_exit_lpr_id,
            "travelDuration": travel_duration,
            "tollTariffID": tariff_id,
            "tariffRate": tariff_rate,
            "balanceBefore": balance_before,
            "balanceAfter": balance_after,
            "status": "Completed",
            "createdAt": now
        })
        print(f"[FIRESTORE TOLL] JOURNEY SUCCESS: Completed transaction document mapping {transaction_doc_ref.id} for {winner}.")
        return True
    except Exception as e:
        print(f"[BILLING ENGINE CRASH] Verification pipeline validation error: {e}")
        transaction_doc_ref.update({
            "status": "BillingEngineCrash",
            "createdAt": now,
            "balanceBefore": None,
            "balanceAfter": None
        })
        return False

def process_penalty_billing(next_id, current_exit_lpr_id, winner, vehicle_id, commuter_id, now):
    try:
        penalty_snap = db.collection("tollPenalty").document("TPID00001").get()
        if penalty_snap.exists:
            penalty_rate = float(penalty_snap.to_dict().get("penaltyRate", 35.0))
        else:
            print("[PENALTY SYSTEM WARNING] TPID00001 doc missing in 'tollPenalty'. Falling back to RM35.00 default.")
            penalty_rate = 35.0

        commuter_doc_ref = db.collection("commuter").document(commuter_id)
        commuter_snap = commuter_doc_ref.get()

        if not commuter_snap.exists:
            commuter_query = db.collection("commuter").where("commuterID", "==", commuter_id).limit(1).get()
            if commuter_query:
                commuter_doc_ref = commuter_query[0].reference
                commuter_data = commuter_query[0].to_dict()
            else:
                print(f"[ACCOUNT ERROR] Commuter profile reference mapping {commuter_id} missing on fine engine route.")
                return
        else:
            commuter_data = commuter_snap.to_dict()

        balance_before = float(commuter_data.get("balance", 0.0))

        if balance_before < penalty_rate:
            balance_after = balance_before
            status_flag = "InsufficientBalanceForPenalty"
            print(f"[WALLET REJECTED] Cannot process penalty fine for {winner}. Balance lower than fine amount.")
        else:
            balance_after = round(balance_before - penalty_rate, 2)
            commuter_doc_ref.update({"balance": balance_after})
            status_flag = "Penalised"
            print(
                f"[WALLET TRANSACTION] PENALTY DEBITED: {commuter_data.get('fullName')}. RM {balance_before:.2f} -> RM {balance_after:.2f}")

        db.collection("tollTransaction").document(next_id).set({
            "tollTransactionID": next_id,
            "vehicleID": vehicle_id,
            "commuterID": commuter_id,
            "entryLprRecordID": None,
            "exitLprRecordID": current_exit_lpr_id,
            "travelDuration": 0.0000,
            "tollTariffID": "TPID00001",
            "tariffRate": penalty_rate,
            "balanceBefore": balance_before,
            "balanceAfter": balance_after,
            "status": status_flag,
            "createdAt": now
        })
        print(
            f"[FIRESTORE TOLL] ILLEGAL EXIT DETECTED: Created penalised transaction {next_id} for {winner} (Fine: RM {penalty_rate:.2f}).")
    except Exception as e:
        print(f"[PENALTY ENGINE CRASH] Verification pipeline error: {e}")


def handle_one_booth_toll(winner, vehicle_id, vehicle_type_id, commuter_id, current_lpr_id):
    try:
        all_tariffs = db.collection("tollTariff").get()
        tariff_match = None
        for t_doc in all_tariffs:
            td = t_doc.to_dict()
            if td.get("entryTollLocationID") == SELECTED_LOCATION_ID and \
                    td.get("exitTollLocationID") == SELECTED_LOCATION_ID and \
                    td.get("vehicleTypeID") == vehicle_type_id:
                tariff_match = td
                break

        if not tariff_match:
            print(f"[TARIFF ERROR] No open tariff pattern found for location context '{SELECTED_LOCATION_ID}'.")
            return

        tariff_rate = float(tariff_match.get("tariffRate"))
        tariff_id = tariff_match.get("tariffID")

        commuter_query = db.collection("commuter").where("commuterID", "==", commuter_id).limit(1).get()
        if not commuter_query:
            print(
                f"[ACCOUNT ERROR] Commuter profile reference mapping {commuter_id} missing on open toll processing loop.")
            return

        commuter_doc_ref = commuter_query[0].reference
        commuter_data = commuter_query[0].to_dict()
        balance_before = float(commuter_data.get("balance", 0.0))

        next_id = get_sequential_id("tollTransaction", "TTID")
        now = datetime.utcnow()

        if balance_before < tariff_rate:
            print(f"[WALLET REJECTED] Open toll transaction halted for {winner}. Balance insufficient.")
            db.collection("tollTransaction").document(next_id).set({
                "tollTransactionID": next_id,
                "vehicleID": vehicle_id,
                "commuterID": commuter_id,
                "entryLprRecordID": current_lpr_id,
                "exitLprRecordID": current_lpr_id,
                "travelDuration": 0.0000,
                "tollTariffID": tariff_id,
                "tariffRate": tariff_rate,
                "balanceBefore": balance_before,
                "balanceAfter": balance_before,
                "status": "InsufficientBalance",
                "createdAt": now
            })
            return

        balance_after = round(balance_before - tariff_rate, 2)
        commuter_doc_ref.update({"balance": balance_after})

        db.collection("tollTransaction").document(next_id).set({
            "tollTransactionID": next_id,
            "vehicleID": vehicle_id,
            "commuterID": commuter_id,
            "entryLprRecordID": current_lpr_id,
            "exitLprRecordID": current_lpr_id,
            "travelDuration": 0.0000,
            "tollTariffID": tariff_id,
            "tariffRate": tariff_rate,
            "balanceBefore": balance_before,
            "balanceAfter": balance_after,
            "status": "Completed",
            "createdAt": now
        })
        print(
            f"[FIRESTORE TOLL] OPEN TOLL SUCCESS: Instantly charged {winner} RM {tariff_rate:.2f} via transaction {next_id} at {SELECTED_LOCATION_DESC}.")
    except Exception as e:
        print(f"[OPEN TOLL ENGINE CRASH] Error processing direct billing sequence: {e}")


def finalize_track(track_id, last_valid_crop):
    global processed_tracks

    with data_lock:
        if track_id in processed_tracks:
            return
        if track_id not in track_plate_candidates:
            return
        candidates = track_plate_candidates[track_id]

    if len(candidates) < 3:
        with data_lock:
            if track_id in track_plate_candidates:
                del track_plate_candidates[track_id]
        return

    counts = Counter(candidates)
    winner, win_count = counts.most_common(1)[0]
    confidence = win_count / len(candidates)

    with data_lock:
        processed_tracks.add(track_id)

    append_to_backup_csv(winner, track_id)

    if confidence < 0.60:
        print(f"[TRACK FINALIZER] Track {track_id} dropped due to low confidence metrics ({confidence:.2f}).")
        return

    winner = winner.strip().upper()
    now = datetime.utcnow()

    if winner in recent_passages and not IS_SHUTTING_DOWN:
        time_delta = (now - recent_passages[winner]).total_seconds()
        if time_delta < PASSAGE_WINDOW:
            return

    recent_passages[winner] = now

    vehicles_ref = db.collection("vehicle")
    query = vehicles_ref.where("licensePlate", "==", winner).limit(1).get()

    vehicle_id = None
    vehicle_data = None

    if query:
        vehicle_id = query[0].id
        vehicle_data = query[0].to_dict()
    else:
        all_vehicles = vehicles_ref.get()
        best_score = 0.0
        for doc in all_vehicles:
            v_data = doc.to_dict()
            db_plate = str(v_data.get("licensePlate", "")).strip().upper()
            if db_plate == winner:
                best_score = 1.0
                vehicle_id = doc.id
                vehicle_data = v_data
                break
            score = similarity(winner, db_plate)
            if score > best_score and score >= 0.70:
                best_score = score
                vehicle_id = doc.id
                vehicle_data = v_data

    if not vehicle_data:
        print(f"[FIRESTORE ERROR] Tracked Plate {winner} is not registered in system maps.")
        create_lpr_record(winner, confidence, "UNREGISTERED", track_id,
                          "ENTRY" if FORCE_MODE in ["ENTER_ONLY", "ENTRY_EQUAL_EXIT"] else "EXIT", last_valid_crop)
        return

    vehicle_type_id = vehicle_data.get("vehicleTypeID")
    commuter_id = vehicle_data.get("commuterID")
    transactions_ref = db.collection("tollTransaction")

    # Open System Flow
    if SELECTED_TOLL_TYPE.strip().capitalize() == "Open":
        current_lpr_id = create_lpr_record(winner, confidence, vehicle_id, track_id, "ENTRY_EXIT", last_valid_crop)
        handle_one_booth_toll(winner, vehicle_id, vehicle_type_id, commuter_id, current_lpr_id)

    # Closed Highway System Flow
    else:
        # Case 1: Entry gate
        if FORCE_MODE == "ENTER_ONLY":
            current_lpr_id = create_lpr_record(winner, confidence, vehicle_id, track_id, "ENTRY", last_valid_crop)
            next_id = get_sequential_id("tollTransaction", "TTID")

            # Set balanceAfter to None for a new entry
            transactions_ref.document(next_id).set({
                "tollTransactionID": next_id,
                "vehicleID": vehicle_id,
                "commuterID": commuter_id,
                "entryLprRecordID": current_lpr_id,
                "exitLprRecordID": None,
                "travelDuration": 0.0000,
                "tollTariffID": None,
                "tariffRate": None,
                "balanceBefore": None,
                "balanceAfter": None,
                "status": "Pending",
                "createdAt": now
            })
            print(f"[FIRESTORE TOLL] ENTRY REGISTERED: Journey tracking session {next_id} initialized [Pending].")

        # Case 2: Exit gate
        elif FORCE_MODE == "EXIT_ONLY":
            current_lpr_id = create_lpr_record(winner, confidence, vehicle_id, track_id, "EXIT", last_valid_crop)

            try:
                open_entry_query = transactions_ref.where("vehicleID", "==", vehicle_id) \
                    .where("status", "==", "Pending") \
                    .order_by("createdAt", direction=firestore.Query.DESCENDING) \
                    .limit(1).get()
            except google.api_core.exceptions.FailedPrecondition:
                streamed_docs = transactions_ref.where("vehicleID", "==", vehicle_id) \
                    .where("status", "==", "Pending").get()
                open_entry_query = sorted(streamed_docs, key=lambda d: d.get("createdAt") or datetime.min,
                                          reverse=True)[:1]

            if not open_entry_query:
                print(f"[TOLL WARNING] Cannot find matching 'Pending' entry for {winner}. Executing fine engine...")
                next_id = get_sequential_id("tollTransaction", "TTID")
                process_penalty_billing(next_id, current_lpr_id, winner, vehicle_id, commuter_id, now)
            else:
                entry_doc = open_entry_query[0]
                entry_doc_ref = entry_doc.reference
                entry_data = entry_doc.to_dict()

                entry_lpr_id = entry_data.get("entryLprRecordID")

                # Find where the vehicle entered the highway
                entry_location_id = None
                entry_timestamp = now

                if entry_lpr_id:
                    lpr_snap = db.collection("lprRecord").document(entry_lpr_id).get()
                    if lpr_snap.exists:
                        # Get the entry location ID from the database record
                        entry_location_id = lpr_snap.to_dict().get("tollLocationID")
                        entry_timestamp = lpr_snap.to_dict().get("capturedAt", now)

                # Use default location if the database info is missing
                if not entry_location_id:
                    entry_location_id = SELECTED_LOCATION_ID

                print(
                    f"[TOLL ENGINE] Linked pending entry match found from origin location context '{entry_location_id}'. Saving financials...")
                process_exit_billing(
                    transaction_doc_ref=entry_doc_ref, entry_time=entry_timestamp,
                    entry_location_id=entry_location_id, current_exit_lpr_id=current_lpr_id,
                    winner=winner, vehicle_id=vehicle_id, vehicle_type_id=vehicle_type_id,
                    commuter_id=commuter_id, now=now
                )

    with data_lock:
        if track_id in track_plate_candidates:
            del track_plate_candidates[track_id]


def preprocess_for_ocr(plate_crop):
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
    thresholded = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 5
    )
    return enhanced, thresholded


def run_ocr(image):
    results = ocr_model.ocr(image, cls=False)
    texts = []
    if results and results[0]:
        for line in results[0]:
            text, _ = line[1]
            texts.append(text.upper())
    return texts


def ocr_worker():
    while True:
        try:
            item = ocr_queue.get(timeout=1)
            if item is None:
                break
            track_id, plate_crop = item
            enhanced, thresholded = preprocess_for_ocr(plate_crop)
            ocr_candidates = []

            for variant in [plate_crop, enhanced, thresholded]:
                texts = run_ocr(variant)
                ocr_candidates.extend(texts)

            valid_candidates = []
            for text in ocr_candidates:
                clean_text = re.sub(r'[^A-Z0-9]', '', text)
                normalized_text = normalize_plate(clean_text)
                if valid_plate(normalized_text):
                    valid_candidates.append(normalized_text)

            if valid_candidates:
                best_frame_candidate = Counter(valid_candidates).most_common(1)[0][0]
                with data_lock:
                    historical_candidates = track_plate_candidates[track_id]
                    for existing in historical_candidates:
                        if similarity(existing, best_frame_candidate) > 0.85:
                            best_frame_candidate = existing
                            break
                    track_plate_candidates[track_id].append(best_frame_candidate)
                    most_common = max(set(track_plate_candidates[track_id]), key=track_plate_candidates[track_id].count)
                    plate_text_final[track_id] = most_common
                    plate_to_ids[most_common].add(track_id)
            ocr_queue.task_done()
        except queue.Empty:
            continue


ocr_thread = threading.Thread(target=ocr_worker, daemon=True)
ocr_thread.start()

frame_count = 0
track_crops_memory = {}


def process_frame(frame):
    global frame_count, active_tracks
    frame_count += 1

    results = model.predict(frame, imgsz=640, conf=0.4, verbose=False)[0]
    detections = []
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        detections.append(([x1, y1, x2 - x1, y2 - y1], conf, 'plate'))

    tracks = tracker.update_tracks(detections, frame=frame)
    current_tracks = set()

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        current_tracks.add(track_id)

        h, w, _ = frame.shape
        l, t, r, b = map(int, track.to_ltrb())
        l = max(0, min(l, w - 1))
        r = max(0, min(r, w - 1))
        t = max(0, min(t, h - 1))
        b = max(0, min(b, h - 1))

        plate_crop = frame[t:b, l:r]
        if plate_crop.size == 0:
            continue

        track_crops_memory[track_id] = plate_crop.copy()

        if frame_count % 5 == 0:
            plate_crop_resized = cv2.resize(plate_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            try:
                ocr_queue.put_nowait((track_id, plate_crop_resized))
            except queue.Full:
                pass

        with data_lock:
            label = plate_text_final.get(track_id, "Detecting...")

        cv2.rectangle(frame, (l, t), (r, b), (0, 255, 0), 2)
        text = f"ID:{track_id} {label}"
        (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(frame, (l, t - text_height - baseline - 4), (l + text_width + 4, t), (255, 255, 255), -1)
        cv2.putText(frame, text, (l + 2, t - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)

    lost_tracks = active_tracks - current_tracks
    for lost_id in lost_tracks:
        last_crop = track_crops_memory.pop(lost_id, None)
        threading.Thread(target=finalize_track, args=(lost_id, last_crop), daemon=True).start()

    active_tracks.clear()
    active_tracks.update(current_tracks)

    if frame_count % 30 == 0:
        captured_at_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"output/annotated_results/{captured_at_str}.jpg"
        cv2.imwrite(filename, frame)


# --- Setup the camera capture ---
cam_index = 1
cap = cv2.VideoCapture(cam_index)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Keep only 1 frame to prevent video delays

if not cap.isOpened():
    print(f"Error: Could not open camera at index {cam_index}.")
    exit(1)

print("\n--- LPR GATEWAY RUNNING ---")
print(f"Active Site Location: {SELECTED_LOCATION_DESC}")
print("Press 'q' inside the video window to stop tracking safely.\n")

prev_time = time.time()
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame from camera.")
            break

        process_frame(frame)

        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time)
        prev_time = curr_time

        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("License Plate Recognition Toll System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n['q' Pressed] Initiating safe graceful shutdown database flush pipeline...")
            break
except KeyboardInterrupt:
    print("\n[Ctrl+C Detected] Initiating safe graceful shutdown pipeline...")

# Stop the camera and close all windows
cap.release()
cv2.destroyAllWindows()

# Process any remaining vehicles before closing
if active_tracks:
    print(f"[SHUTDOWN ENGINE] Found {len(active_tracks)} targets remaining in buffer. Flushing to Firestore...")
    IS_SHUTTING_DOWN = True
    active_threads = []
    for remaining_id in list(active_tracks):
        last_crop = track_crops_memory.pop(remaining_id, None)
        t = threading.Thread(target=finalize_track, args=(remaining_id, last_crop), daemon=False)
        t.start()
        active_threads.append(t)
    for t in active_threads:
        t.join()

ocr_queue.put(None)
ocr_thread.join()

print("\n[SYSTEM STATUS] Active loop finalized. Check local file realtime_lpr_results.csv. Exit clean.\n")