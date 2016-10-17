import argparse
import socket

import HW3

MAXCON=4
HOST='0.0.0.0'

def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="The port to listen on.")
    args = parser.parse_args()
    return args

def do_client_interaction(connection):

    while True:
        smtpssm = HW3.SMTPServerStateMachine(input_function=read_line_from_socket)
        smtpssm.cnxn = connection
        smtpssm.mode = "server"
        smtpssm.enter_mail_from()

def read_line_from_socket(caller):
    """
    Given a connection, read a single "line"
    ending in a newline char
    """
    line = ""
    buf = caller.cnxn.recv(64)
    while(len(buf) > 0 and '\n' not in buf):
        line += buf.decode()
        buf = caller.cnxn.recv(64)
    line = (line + buf.decode())
    line = line.replace('\n', '')
    line = line.replace('\r', '')
    return line

def serve(port):
    sock = socket.socket()
    
    sock.bind((HOST, int(port)))
    sock.listen(MAXCON)

    while True:
        cnxn, addr = sock.accept()
        do_client_interaction(cnxn)


if __name__ == "__main__":

    args = make_parser()
    serve(args.port)
