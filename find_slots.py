import cv2
import numpy as np
from PIL import Image

def find_white_slots(image_path):
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    
    # Create mask for near-white pixels (e.g. R, G, B all > 240)
    mask = ((arr[:,:,0] > 240) & (arr[:,:,1] > 240) & (arr[:,:,2] > 240)).astype(np.uint8) * 255
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    slots = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 100 and h > 100 and w < arr.shape[1] * 0.9: # filter out noise and the whole image
            # check if the bounding box is a valid rectangle
            slots.append({"x": x, "y": y, "w": w, "h": h, "ratio": w/h})
            
    # Sort slots from top to bottom
    slots.sort(key=lambda s: s["y"])
    
    print(f"Found {len(slots)} white slots in {image_path}:")
    for i, s in enumerate(slots):
        print(f"Slot {i+1}: {s}")

if __name__ == "__main__":
    find_white_slots("assets/strip-1.png")
