import cv2
from ultralytics import YOLO
import numpy as np

model = YOLO('yolov8n.pt')
video_path = 'assets/sample_video.mp4'
cap = cv2.VideoCapture(video_path)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)
    detections = results[0].boxes

    for box in detections:
        cls = int(box.cls.item())
        if cls == 3:  # classe 3 = "motorbike" em COCO
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imshow("FleetZone - YOLOv8 Deteção", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
