import cv2
from kafka import KafkaConsumer
import argparse
from io import BytesIO
from PIL import Image
import requests
import numpy as np
import json

TOPIC = 'model_results'

URL = 'http://10.249.77.82:8000/'

def draw_rectangle(title, device_id, file_name, boxes):
    url_path = URL + device_id + '/' + file_name
    resp = requests.get(url_path)
    arr = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    print(img.shape)
    for box in boxes:
        text = box['activities']
        [x, y, w, h] = box['loc']
        # Get the unique color for this class
        color = [0,255,0]
        # Draw the bounding box rectangle and label on the image
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        if len(text) > 0:
            cv2.putText(img, text[0], (x+5, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    print('ready to show')
    cv2.imshow(title, img)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', help='device_id to be extract image frame')
    args = parser.parse_args()
    device_arg = args.device
    if device_arg == None:
        raise RuntimeError("No device id to supply!")
    kafka_consumer = KafkaConsumer(TOPIC, bootstrap_servers= ['10.249.77.87:9092'], api_version=(0,10))

    title = "device_id:" + device_arg
    cv2.namedWindow(title)

    for msg in kafka_consumer:
        try:
            raw_value = msg.value.decode('utf-8')
            result_json = json.loads(raw_value)
            device_id = result_json['device_id']
            file_name = result_json['file_name']
            boxes = result_json['boxes']
            draw_rectangle(title, device_id, file_name, boxes)
            if cv2.waitKey(1) == 27:
                break
        except Exception as e:
            pass
