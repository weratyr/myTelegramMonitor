#!/usr/bin/env python3

import logging, socket, struct, os, inspect, _thread, time, signal, sys

from datetime import datetime

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from pystemd.systemd1 import Unit, Manager

sys.path.append('/etc/myTelegramBot')
from config import *


hostname = socket.gethostname()



# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

myBot = None

FIFO = '/var/run/myTelegramBot'

shortKeys = {
        "m": "microfw",
        "k": "keepalived",
        "pall": "192.168.5.113 192.168.5.100 192.168.5.86 8.8.8.8"
    }

def check_ping(hostname):
    exitCode = os.system("ping -c 1 -4 %s" % hostname)
    if exitCode == 0:
        result = "%s:  Active" % hostname
    else:
        result = "%s:  Error" % hostname

    return result


def lookForShortKey(systemdServiceName): 
    if systemdServiceName[0] in shortKeys:
        systemdServiceName = shortKeys.get(systemdServiceName[0])
    else:
        systemdServiceName = systemdServiceName[0]
    return systemdServiceName


def setupNamedPipe(): 
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)
    
    while True:
        with open(FIFO) as fifo:
            for line in fifo:
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                myMessage = "%s %s:\n %s"  % (current_time, hostname, line)
                myBot.send_message(CHATID, myMessage)


'''
    Network action commands
'''
def show_gw(update: Update, context: CallbackContext) -> None:
    """Read the default gateway directly from /proc."""
    with open("/proc/net/route") as routeFile:
        for line in routeFile:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                # If not default route or not RTF_GATEWAY, skip it
                continue
            update.message.reply_text(f'%s: Current GW is -> %s' % 
                    (hostname, socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))))


def inet_ping(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) > 0:
        args = lookForShortKey(args)
        if len(args.split(' ')) > 1:
            pingResult = ""
            for arg in args.split(' '): 
                pingResult += "%s \n" % check_ping(arg)
            update.message.reply_text(f'Ping Result: \n {pingResult}')
        else:
            pingResult = check_ping(args)
            update.message.reply_text(f'Ping Result:\n {pingResult}')
    else: 
        update.message.reply_text(f'/p <ip|shortKey>')





'''
    Systemd action commands
'''

'''
    Systemd status command
    /sstatus <systemd service name| short key>
'''
def systemd_status(update: Update, context: CallbackContext) -> None:
    systemdServiceName = context.args
    if len(systemdServiceName) > 0:
        systemdServiceName = lookForShortKey(systemdServiceName)
   
        unit = Unit("%s.service" % systemdServiceName, _autoload=True)
        update.message.reply_text(f'%s: %s -> %s(%s)' % 
            (hostname, systemdServiceName, unit.Unit.ActiveState.decode('utf-8'), unit.Unit.SubState.decode('utf-8')))
    else: 
        update.message.reply_text(f'/sstatus <systemd service name>')

'''
    Systemd start command
    /sstart <systemd service name| short key>
'''
def systemd_start(update: Update, context: CallbackContext) -> None:
    systemdServiceName = context.args
    if len(systemdServiceName) > 0:
        systemdServiceName = lookForShortKey(systemdServiceName)

        update.message.reply_text(f'%s: Start %s \n' % (hostname, systemdServiceName)  )   
        manager = Manager()
        manager.load()
        manager.Manager.StartUnit("%s.service" % systemdServiceName, "replace")
    else: 
        update.message.reply_text(f'/srestart <systemd service name>')

'''
    Systemd stop command
    /sstop <systemd service name| short key>
'''
def systemd_stop(update: Update, context: CallbackContext) -> None:
    systemdServiceName = context.args
    if len(systemdServiceName) > 0:
        systemdServiceName = lookForShortKey(systemdServiceName)

        update.message.reply_text(f'%s: Stop %s  \n' % (hostname, systemdServiceName)  )
        manager = Manager()
        manager.load()
        manager.Manager.StopUnit("%s.service" % systemdServiceName, "replace")
    else: 
        update.message.reply_text(f'/srestart <systemd service name>')

'''
    Systemd restart command
    /srestart <systemd service name| short key>
'''
def systemd_restart(update: Update, context: CallbackContext) -> None:
    systemdServiceName = context.args
    if len(systemdServiceName) > 0:
        systemdServiceName = lookForShortKey(systemdServiceName)

        update.message.reply_text(f'%s: Restart %s  \n' % (hostname, systemdServiceName)  )
        manager = Manager()
        manager.load()
        manager.Manager.RestartUnit("%s.service" % systemdServiceName, "replace")
    else: 
        update.message.reply_text(f'/srestart <systemd service name>')





'''
    Other commands
'''
def help(update: Update, context: CallbackContext) -> None:
    bot: Bot = context.bot

    shortKeyStr = ""
    for key in shortKeys: 
        shortKeyStr += "%s -> %s \n" % (key,shortKeys[key])

    update.message.reply_text(f'''
        Help:
        systemd: 
        /sstart <service name> 
        /sstop <service name> 
        /srestart <service name> 
        /sstatus <service name>
        \n 
        /gw  show current GW 
        /p  <host to ping| shortKeys> 
        \n
        Current ShortKeys:
        {shortKeyStr}
        ''')


def handler_signals():
    updater.stop()


def main():

    try: 
       pipeThread = _thread.start_new_thread(setupNamedPipe,()) 
    except Exception as e:
        print(e) 
        print("Could not start named pipe thread!")

    print("Start myBot")
    updater = Updater(APIKEY)

    global myBot 
    myBot = updater.bot

    #updater.dispatcher.add_handler(CommandHandler('hello', hello))
    updater.dispatcher.add_handler(CommandHandler('p', inet_ping))
    updater.dispatcher.add_handler(CommandHandler('gw', show_gw))

    # register systemd actions
    updater.dispatcher.add_handler(CommandHandler('sstatus', systemd_status))
    updater.dispatcher.add_handler(CommandHandler('sstop', systemd_stop))
    updater.dispatcher.add_handler(CommandHandler('sstart', systemd_start))
    updater.dispatcher.add_handler(CommandHandler('srestart', systemd_restart))
    updater.dispatcher.add_handler(CommandHandler('help', help))

    # register SIGINT and SIGTERM
    signal.signal(signal.SIGINT, handler_signals)
    signal.signal(signal.SIGTERM, handler_signals)
    try: 
        updater.start_polling()
        updater.idle()
    except Exception as e: 
        print(e)
    finally: 
        _thread.exit()
        exit()






if __name__ == "__main__":
    main()




