import pic_persist
import file_server
import collect_result

if __name__ == "__main__":
    pm = pic_persist.PersistanceManager()
    fs = file_server.FileServer()
    cm = collect_result.CollectManager()
    pm.start()
    fs.start()
    cm.start()
