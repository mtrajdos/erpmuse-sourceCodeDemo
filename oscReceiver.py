"""
Mind Monitor - Minimal EEG OSC Receiver
Coded: James Clutterbuck (2021)
Requires: pip install python-osc
"""
from datetime import datetime
from pythonosc import dispatcher
from pythonosc import osc_server

ip = "192.168.20.161"
port = 5499

def eeg_handler(address: str,*args):
    dateTimeObj = datetime.now()
    printStr = dateTimeObj.strftime("%Y-%m-%d %H:%M:%S.%f")
    for arg in args:
        printStr += ","+str(arg)
    print(printStr)
    
if __name__ == "__main__":
    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/muse/eeg", eeg_handler)

    server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
    print("Listening on UDP port "+str(port))
    server.serve_forever()