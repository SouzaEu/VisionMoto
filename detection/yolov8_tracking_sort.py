import cv2
from ultralytics import YOLO
from sort import Sort
import numpy as np

model = YOLO('yolov8n.pt')
video_path = 'assets/sample_video.mp4'
cap = cv2.VideoCapture(video_path)
tracker = Sort()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)
    detections = results[0].boxes

    dets = []
    for box in detections:
        cls = int(box.cls.item())
        if cls == 3:  # classe 3 = "motorbike" em COCO
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf.item()
            dets.append([x1, y1, x2, y2, conf])

    dets_np = np.array(dets)
    if len(dets_np) == 0:
        tracks = np.empty((0, 5))
    else:
        tracks = tracker.update(dets_np)

    for track in tracks:
        if len(track) == 5:
            x1, y1, x2, y2, track_id = track.astype(int)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, f'ID {track_id}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    cv2.imshow("FleetZone - Rastreamento YOLOv8 + SORT", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
