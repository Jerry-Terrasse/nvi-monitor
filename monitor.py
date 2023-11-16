#!/bin/python3

import os
import sys
import subprocess
import json

import smtplib
from email.message import EmailMessage

server_name = subprocess.check_output(['hostname']).decode('utf-8').strip()
config: dict = {}

def report(idx: int, sta: list[int]):
    message = EmailMessage()
    message['Subject'] = f"GPU {idx} on {server_name} is too hot"
    message['From'] = config['email_sender']
    message['To'] = config['email_receiver']
    message.set_content(f"""\
average temperature is {sum(sta) / len(sta)}°C
history temperature: {sta[::-1]}
""")
    try:
        with smtplib.SMTP_SSL(config['smtp_server'], 465) as smtp:
            smtp.login(config['email_sender'], config['smtp_key'])
            smtp.send_message(message)
    except Exception as e:
        print(e)
        print('failed to send email')

def main(thresh: int, interval: int = 10, queue_size: int = 10):
    status: dict[int, list[int]] = {}
    monitor = subprocess.Popen(['nvidia-smi', 'dmon', '-s', 'p', '-d', str(interval)], stdout=subprocess.PIPE)
    while True:
        line = monitor.stdout.readline().decode('utf-8').strip() # type: ignore
        print(line)
        if line.startswith('#'):
            continue
        idx, _, t, _ = line.split()
        idx = int(idx)
        if idx not in status:
            status[idx] = []
        sta = status[idx]
        
        if len(sta) >= queue_size:
            sta.pop(0)
        sta.append(int(t))
        
        if len(sta) >= queue_size and sum(sta) / len(sta) > thresh:
            report(idx, sta)
            sta.clear() # don't report repeatedly

if __name__ == '__main__':
    work_dir = os.path.dirname(os.path.realpath(__file__))
    config = json.load(open(os.path.join(work_dir, 'config.json')))
    
    thresh = config['thresh']
    interval = config['interval']
    queue_size = config['queue_size']
    
    if len(sys.argv) > 1:
        thresh = int(sys.argv[1])
    
    main(thresh, interval, queue_size)