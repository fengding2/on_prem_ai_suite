from app_global_imports import *
import numpy as np
import os
from PIL import Image
import time

AREA_IMAGE_PATH = CURRENT_DIR + '/area_map/'
BLUE    = np.array([0, 0, 255], dtype=np.uint8)     ## code 0
GREEN   = np.array([0, 255, 0], dtype=np.uint8)     ## code 1
RED     = np.array([255, 0, 0], dtype=np.uint8)     ## code 2
WHITE   = np.array([255, 255, 255], dtype=np.uint8) ## code 3

LEFT_CAMERA_AREA = {0: 'chat_sofa', 1: 'work_sofa', 2: 'round_table', 3: 'hall'}
RIGHT_CAMERA_AREA = {0: 'dining_table', 1: 'hall', 2: 'stairs', 3: 'work_sofa'}
CAMERA_AREA_DICT = {'b827ebf39c8c': LEFT_CAMERA_AREA, 'b827ebc347bd': RIGHT_CAMERA_AREA}

class AreaSlicer():
    AREA_DICT = {}

    @staticmethod
    def pre_load():
        img_files = os.listdir(AREA_IMAGE_PATH)
        for file_name in img_files:
            if file_name.endswith('png') or \
               file_name.endswith('jpeg') or \
               file_name.endswith('jpg'):
                device_id = file_name.split('.')[0]
                img_file_path = AREA_IMAGE_PATH + file_name
                txt_file_path = AREA_IMAGE_PATH + device_id + '.txt'
                s = time.time()
                if os.path.exists(txt_file_path):
                    AreaSlicer._read_from_txt(device_id, txt_file_path)
                else:
                    AreaSlicer._read_from_img(device_id, img_file_path, txt_file_path)
                e = time.time()
                print(e-s)

    @staticmethod
    def _read_from_img(device_id, img_path, txt_path):
        img = Image.open(img_path)
        pix = np.array(img)
        pix_map = AreaSlicer.pix_encode(pix)
        np.savetxt(txt_path, pix_map, fmt='%d')
        AreaSlicer.AREA_DICT[device_id] = pix_map 

    @staticmethod
    def _read_from_txt(device_id, file_path):
        pix_map = np.loadtxt(file_path, dtype=np.int)
        AreaSlicer.AREA_DICT[device_id] = pix_map

    @staticmethod
    def pix_encode(pix):
        height, width, c = pix.shape
        id_map = np.zeros(shape=(height, width), dtype=np.int32)
        for y in range(0, height):
            for x in range(0, width):
                c = pix[y, x, :]
                if np.abs(c - BLUE).sum() == 0:
                    aid = 0
                elif np.abs(c - GREEN).sum() == 0:
                    aid = 1
                elif np.abs(c - RED).sum() == 0:
                    aid = 2
                elif np.abs(c - WHITE).sum() == 0:
                    aid = 3
                else:
                    aid = -1
                
                id_map[y, x] = aid
        return id_map

    @staticmethod
    def _get_encoding(device_id, x, y, w, h):
        foot_y, foot_x = AreaSlicer._get_foot(x, y, w, h)
        area_dict = AreaSlicer.AREA_DICT.get(device_id)
        if area_dict is None:
            return -1
        if foot_y > area_dict.shape[0] or foot_x > area_dict.shape[1]:
            return -1
        return area_dict[foot_y, foot_x]


    @staticmethod
    def _get_foot(x, y, w, h):
        sv = min(max(w / h, 0.25), 1)
        sv = (sv - 0.25) / 0.75
        sv = (sv - 0.5) * 2
        return int(y + h + sv * int(h * 0.1)), (x + int(w / 2))

    @staticmethod
    def get_area(device_id, x, y, w, h):
        area_name_dict = CAMERA_AREA_DICT.get(device_id)
        area_code = AreaSlicer._get_encoding(device_id, x, y, w, h)
        if area_code == -1 or area_name_dict is None:
            return 'unknown'
        area_name = area_name_dict.get(area_code)
        if area_name is None:
            return 'unknown'
        return area_name


if __name__ == "__main__":
    AreaSlicer.pre_load()
    print(AreaSlicer.get_area('b827ebc347bd', 367, 84, 57, 180))
