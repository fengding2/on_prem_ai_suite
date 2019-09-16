from kafka import KafkaConsumer
import threading

class CollectManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        
    