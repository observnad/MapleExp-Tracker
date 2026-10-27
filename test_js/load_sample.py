import cv2
import json
import os
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'exp_twenty_pct.png'
    path = os.path.join(os.path.dirname(__file__), '..', 'debug_captures', name)
    img = cv2.imread(path)
    if img is None:
        sys.exit(1)
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
    h, w = rgba.shape[:2]
    json.dump({'width': w, 'height': h, 'data': rgba.flatten().tolist()}, sys.stdout)

if __name__ == '__main__':
    main()
