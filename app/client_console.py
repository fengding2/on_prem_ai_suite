import cmd
import requests
import json
import traceback
import sys

URL_ROOT = 'http://127.0.0.1:5000'
MODIFY_PATH = '/api/modify/'
QUERY_PATH = '/api/query/'

def parse(arg):
    return arg.split()

class AppShell(cmd.Cmd):
    intro = 'Welcome to the on-prem AI shell.\n Type help or ? to list commands.\n'
    prompt = '(on-prem) '

    def do_ls(self, args):
        url = URL_ROOT + QUERY_PATH
        try:
            if args:
                tup = parse(args)
                if len(tup) != 1:
                    print('[Error]ls need one device_id argument')
                device_info = requests.post(url, json={'device_id': tup[0]})
                json_info = json.loads(device_info.text)
                print(json.dumps(json_info, indent=2))
            else:
                device_info = requests.post(url, json={})
                json_info = json.loads(device_info.text)
                print(json.dumps(json_info, indent=2))
        except:
            print(traceback.format_exc())
        

    def do_instruct(self, args):
        url = URL_ROOT + MODIFY_PATH
        tup = parse(args)
        if len(tup) != 2:
            print('[Error]instruct need 2 arguments')
            return
        device_id = tup[0]
        instruction = tup[1]
        try:
            device_info = requests.post(url, json={'device_id': device_id, 'instruction': instruction})
            json_info = json.loads(device_info.text)
            print(json.dumps(json_info, indent=2)) 
        except:
            print(traceback.format_exc())

    def do_interval(self, args):
        url = URL_ROOT + MODIFY_PATH
        tup = parse(args)
        if len(tup) != 2:
            print('[Error]interval need 2 arguments')
            return
        device_id = tup[0]
        duration = tup[1]
        try:
            device_info = requests.post(url, json={'device_id': device_id, 'duration': duration})
            json_info = json.loads(device_info.text)
            print(json.dumps(json_info, indent=2)) 
        except:
            print(traceback.format_exc())
    
    def do_exit(self, *args):
        print('Bye!')
        return True

    def do_quit(self, *args):
        print('Bye!')
        return True

if __name__ == "__main__":
    AppShell().cmdloop()