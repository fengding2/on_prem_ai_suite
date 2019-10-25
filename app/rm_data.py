import os
import argparse

#os.remove('./t.txt')









if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', help='deleting file interval', type=int)
    args = parser.parse_args()
    interval = args.interval
    if not interval:
        print('no interval')
    