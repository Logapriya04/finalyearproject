import os
import torch  # type: ignore
import numpy as np  # type: ignore
import cv2  # type: ignore
from django.conf import settings  # type: ignore
from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import authenticate, login, logout  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.auth.decorators import login_required  # type: ignore
from django.http import JsonResponse, StreamingHttpResponse  # Added StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from django.core.files.storage import default_storage  # type: ignore
from .models import CustomUser
from ultralytics import YOLO  # type: ignore


# ✅ Load YOLO Model (Ensure `yolov8n.pt` is present)
model_path = os.path.join(settings.BASE_DIR, "yolov8n.pt")
if not os.path.exists(model_path):
    raise FileNotFoundError("⚠️ YOLO model not found! Download `yolov8n.pt` and place it in the project folder.")

model = YOLO(model_path)  # Load YOLOv8 model


# ----------------- STATIC PAGES -----------------
def index(request):
    return render(request, 'home/index.html')


def how_it_works(request):
    return render(request, 'home/how_it_works.html')


def about(request):
    return render(request, 'home/about.html')


@login_required(login_url='home:login')
def detection(request):
    return render(request, 'home/detection.html')


def service(request):
    return redirect('https://www.vanjinathanambulanceservice.com/')


def contact(request):
    return render(request, 'home/contact.html')


def help_view(request):
    return render(request, 'home/help.html')


# ----------------- USER AUTHENTICATION -----------------
def register(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not all([username, email, password1, password2]):
            messages.error(request, "All fields are required.")
            return redirect('home:register')

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('home:register')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists! Please log in.")
            return redirect('home:login')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered! Please log in.")
            return redirect('home:login')

        try:
            user = CustomUser.objects.create_user(username=username, email=email, password=password1)
            user.save()
        except Exception as e:
            messages.error(request, f"Error creating user: {e}")
            return redirect('home:register')

        user = authenticate(request, username=username, password=password1)
        if user:
            login(request, user)
            messages.success(request, "✅ Registration successful!")
            return redirect('home:main')
        else:
            messages.error(request, "Authentication failed. Please log in manually.")
            return redirect('home:login')

    return render(request, 'home/register.html')


def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect("home:login")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, "✅ Login successful!")
            return redirect("home:main")
        else:
            messages.error(request, "❌ Invalid username or password.")
            return redirect("home:login")

    return render(request, "home/login.html")


def user_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect("home:index")


@login_required(login_url='home:login')
def main(request):
    return render(request, "home/main.html")


# ----------------- AMBULANCE DETECTION -----------------
@csrf_exempt
def detect_ambulance(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        file_path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)

        # Get absolute path of the saved file
        image_path = os.path.join(settings.MEDIA_ROOT, file_path)

        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            return JsonResponse({"error": "Invalid image file"}, status=400)

        # 🔍 Run YOLOv8 Detection
        results = model(image)

        # ✅ Extract detected objects
        detected_objects = []
        ambulance_detected = False  # Flag for detection

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Get bounding box
                conf = box.conf[0].item()  # Confidence score
                class_id = int(box.cls[0].item())  # Class ID
                label = model.names[class_id]  # Get class name

                detected_objects.append({"label": label, "confidence": conf, "bbox": [x1, y1, x2, y2]})

                # 🚑 Check for possible ambulance classes
                if label in ["truck", "car", "bus"]:
                    ambulance_detected = True  # Flag as detected
                    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)  # Draw bounding box
                    cv2.putText(image, f"Ambulance? {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Ensure the processed directory exists
        processed_dir = os.path.join(settings.MEDIA_ROOT, "processed")
        os.makedirs(processed_dir, exist_ok=True)

        # Save processed image
        processed_image_path = os.path.join(processed_dir, uploaded_file.name)
        cv2.imwrite(processed_image_path, image)

        return JsonResponse({
            "detected": ambulance_detected,
            "output_image": settings.MEDIA_URL + f"processed/{uploaded_file.name}",
            "message": "✅ Possible Ambulance detected!" if ambulance_detected else "❌ No Ambulance detected.",
            "detections": detected_objects
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


# ----------------- IMAGE & VIDEO UPLOAD -----------------
@csrf_exempt
def upload_image(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        file_path = default_storage.save(f"uploads/{file.name}", file)
        image_path = os.path.join(settings.MEDIA_ROOT, file_path)

        # Load the image
        image = cv2.imread(image_path)

        # Run YOLO detection
        results = model(image)

        # Check for ambulance detection (Filtering by class ID)
        ambulance_detected = False
        detected_boxes = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0].item())  # Get class ID
                label = model.names[class_id]  # Get class label
                confidence = box.conf[0].item()  # Get confidence score

                # ✅ Only detect "ambulance" and ignore other vehicles
                if label.lower() == "ambulance" and confidence > 0.85:  
                    ambulance_detected = True
                    detected_boxes.append({
                        "x1": int(box.xyxy[0][0]),
                        "y1": int(box.xyxy[0][1]),
                        "x2": int(box.xyxy[0][2]),
                        "y2": int(box.xyxy[0][3]),
                        "confidence": round(confidence, 0.80),
                        "label": label
                    })

        return JsonResponse({
            "detected": ambulance_detected,
            "boxes": detected_boxes,
            "message": "🚑 Ambulance Detected!" if ambulance_detected else "No Ambulance Found."
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def upload_video(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        file_path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)
        return JsonResponse({"message": "File uploaded successfully!", "file_path": settings.MEDIA_URL + file_path})

    return JsonResponse({"error": "Invalid request"}, status=400)



# ----------------- CCTV STREAM FUNCTION -----------------
def generate_frames():
    cap = cv2.VideoCapture(0)  # Open webcam (or use a CCTV stream URL)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # 🔍 Run YOLO detection on each frame
        results = model(frame)

        # 🚑 Draw bounding boxes for detected ambulances
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = box.conf[0].item()
                class_id = int(box.cls[0].item())
                label = model.names[class_id]

                # If detected object is a possible ambulance
                if label in ["truck", "car", "bus"]:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(frame, f"Ambulance? {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Encode the frame in JPEG format
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


def cctv_stream(request):
    return StreamingHttpResponse(generate_frames(), content_type="multipart/x-mixed-replace; boundary=frame")
