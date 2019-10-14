import numpy
import cv2
from kafka import KafkaConsumer
import argparse
from io import BytesIO
from PIL import Image

SAMPLING_TOPIC = 'device_sampling'

def img2nparray(stream):
    image = Image.open(BytesIO(stream))
    return cv2.cvtColor(numpy.asarray(image),cv2.COLOR_RGB2BGR)  

drawing = False # true if mouse is pressed
mode = True # if True, draw rectangle. Press 'm' to toggle to curve
ix,iy = -1,-1

# mouse callback function
def draw_circle(event,x,y,flags,param):
    global ix,iy,drawing,mode

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix,iy = x,y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            if mode == True:
                cv2.rectangle(img,(ix,iy),(x,y),(0,255,0),-1)
            else:
                cv2.circle(img,(x,y),5,(0,0,255),-1)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        if mode == True:
            cv2.rectangle(img,(ix,iy),(x,y),(0,255,0),-1)
        else:
            cv2.circle(img,(x,y),5,(0,0,255),-1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', help='device_id to be extract image frame')
    args = parser.parse_args()
    device_arg = args.device
    if device_arg == None:
        raise RuntimeError("No device id to supply!")
    kafka_consumer = KafkaConsumer(SAMPLING_TOPIC, bootstrap_servers= ['10.249.77.87:9092'], api_version=(0,10))
    
    img = numpy.zeros((640,480,3), numpy.uint8)
    title = "device_id:" + device_arg
    cv2.namedWindow(title)
    cv2.setMouseCallback(title,draw_circle)

    for msg in kafka_consumer:
        offset = msg.offset
        b_key = msg.key
        filename = b_key.decode('utf-8')
        device_id, _ = filename.split('_')
        if device_id == device_arg:
            b_picstream = msg.value
            title = "device_id:" + device_id
            frame = img2nparray(b_picstream)
            cv2.imshow(title, frame)
        if cv2.waitKey(1) == 27:
            break