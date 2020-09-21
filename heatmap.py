import cv2
import numpy as np

# Load image, grayscale, Gaussian blur, and Otsu's threshold
#cap = cv2.VideoCapture(0)
cap = cv2.VideoCapture('/Users/mansoor.siddiqui/Workspace/drone/data/stanford_dataset/videos/bookstore/video0/video.mov')
ret, frame = cap.read()

# Resize to make processing faster
frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)

# Blur image to make contours easier to find
radius = 10
ksize = int(2 * round(radius) + 1)
image = cv2.blur(frame, (ksize, ksize))

# Convert to HSV color for filtering
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# Filter out all colors except red
lower_red = np.array([0, 87, 211])
upper_red = np.array([36, 255, 255])

# Create binary mask to detect objects/contours
mask = cv2.inRange(hsv, lower_red, upper_red)

# Find contours and sort using contour area
cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnts = cnts[0] if len(cnts) == 2 else cnts[1]
cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
for c in cnts:
    # Once we hit smaller contours, stop the loop
    if (cv2.contourArea(c) < 100):
        break

    # Draw bounding box around contours and write "Red Object" text
    x, y, w, h = cv2.boundingRect(c)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, 'Red Object', (x, y), font, 1, (0, 255, 0), 2, cv2.LINE_AA)

# Write images to disk for debugging
cv2.imwrite('thresh.png', mask)
cv2.imwrite('image.png', frame)

# Close camera
cap.release()
