from app_global_imports import DATA_DIR
import os
import argparse
import re
from datetime import datetime

reg = re.compile(r'_(\d+).jpe?g')

def del_overdue_file_job(root_path, cur_datetime, interval):
    dir_list = os.listdir(root_path)
    for file_name in dir_list:
        dir_path = root_path + '/' + file_name
        if os.path.isdir(dir_path):
            pic_file_list = os.listdir(dir_path)
            for pic_file_name in pic_file_list:
                if is_file_overdue(pic_file_name, cur_datetime, interval):
                    pic_path = dir_path + '/' + pic_file_name
                    os.remove(pic_path)

def is_file_overdue(file_name, cur_datetime, interval):
    search_results = reg.search(file_name)
    if search_results:
        timestamp = int(search_results.groups()[0])
        file_datetime = datetime.fromtimestamp(timestamp)
        delta = cur_datetime - file_datetime
        if delta.days >= interval:
            return True
        else:
            return False
    else:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', help='deleting file interval', type=int)
    args = parser.parse_args()
    interval = args.interval
    if not interval:
        print('no interval')
    cur_datetime = datetime.now()
    print('rm_data job starts when ' + str(cur_datetime))
    del_overdue_file_job(DATA_DIR, cur_datetime, interval)