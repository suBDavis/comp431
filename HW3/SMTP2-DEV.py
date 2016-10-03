#!/usr/bin/python

# -----------------
# Comp431 FALL 2016
# Brandon Davis
# Homework 3: SMTP2
# -----------------

import sys
import re
import argparse

SPECIAL = ['<', '>', '(', ')', '[', ']', '\\', '.', ',', ';', ':', '@', '"']
WHITESPACE = [' ', '\t']
SP = ' '
AT = '@'

# -----------------
# Exception Classes
# -----------------

# FOR MAL-FORMED COMMANDS
class CommandException(Exception):
    pass

# FOR CORRECT COMMANDS WITH MAL-FORMED ARGS
class SyntaxException(Exception):
    pass

# FOR CORRECT COMMANDS AND ARGS, OUT OF PLACE
class OrderException(Exception):
    pass

# -----------------
# Enumerators
# -----------------

class commands:
    
    MAIL_FROM = "MAIL FROM:"
    RCPT_TO = "RCPT TO:"
    DATA = "DATA"
    END_DATA = "."
    QUIT = "QUIT"
    UNKNOWN = "UNKNOWN"

    CLIENT_FROM = "From:"
    CLIENT_TO = "To:"

    @staticmethod
    def check_equal(cmd1, cmd2):
        return cmd1.lower() == cmd2.lower()

class error:

    BAD_CMD_CODE = "500"
    BAD_SYNTAX_CODE = "501"
    BAD_ORDER_CODE = "503"

    BAD_CMD = BAD_CMD_CODE + " Syntax error: command unrecognized"
    BAD_SYNTAX = BAD_SYNTAX_CODE + " Syntax error in parameters or arguments"
    BAD_ORDER = BAD_ORDER_CODE + " Bad sequence of commands"

class success:

    OK_CODE = "250"
    START_DATA_CODE = "354"

    OK = OK_CODE + " OK"
    START_DATA = START_DATA_CODE + " Start mail input; end with <CRLF>.<CRLF>"

# -----------------
# Helper functions
# -----------------

def log(string, stderr=False):

    if sys.version_info >= (3,0):
        print("Python3 Not supported")
    
    else:
        if stderr:
            print >> sys.stderr, string
        else:
            print string

def parse_path(reverse_path):
    assert(reverse_path[0] == '<')
    assert(reverse_path[-1] == '>')
    assert(reverse_path[1] != ' ')
    assert(reverse_path[-2] != ' ')
    return reverse_path[1:-1]

def parse_mailbox(mailbox): 
    assert('@' in mailbox)
    assert(len(mailbox.split('@')) == 2)
    parse_list = mailbox.split('@')
    assert(len(parse_list[0]) >= 1)
    assert(len(parse_list[1]) >= 1)
    return parse_list[0], parse_list[1]

def parse_local_part(local_part):
    excluded_char_list = SPECIAL + WHITESPACE
    for excluded_char in excluded_char_list:
        assert(excluded_char not in local_part)

    # Verify the string was ASCII
    assert(len(local_part) == len(local_part.encode()))
    return local_part

def parse_domain(domain):
    element_list = domain.split('.')
    for element in element_list:
        assert(len(element)>=2)
    return element_list

def parse_element(element):
    element_pattern = re.compile('^[A-Za-z]+[A-Za-z1-9]+$')
    assert(re.match(element_pattern, element))
    return element

def parse_mailbox_cmd(cmd_header, cmd):
    try:
        reverse_path = cmd[ len(cmd_header) : ].strip()
        mailbox = parse_path(reverse_path)
        local_part, domain = parse_mailbox(mailbox)
        valid_local_part = parse_local_part(local_part)
        element_list = parse_domain(domain)
        element_list = [parse_element(element) for element in element_list]
        return mailbox
    except:
        raise SyntaxException("Syntax malformed")

# -----------------
# Parent State Machine Logic
# -----------------

class SMTPStateMachine:
    """
    Contains:
        wait_for()  # returns desired command from file/stdin
        parse_cmd() # returns parsed command text
        read_line() # reads line from stdin
        read_file() # reads line from file.
    """

    def __init__(self):
        self.mode = "server"
        self.inf = None
        self.to_list = []
        self.mail_from = None
        self.data_list = []

    def wait_for(self, command_list, fromfile=False):
        """
        Waits in a loop for the specified list of commands.
        If the list is empty, return anything.
        """

        return_anything = len(command_list) < 1

        while True:
            
            if fromfile:
                command = self.read_file()
                # DON'T ECHO THE FILE
            else:
                command = self.read_line()
                
                if self.mode == "server":
                    print(command)

            # Replace all whitespace runs with a single space
            command_trimmed = ' '.join(command.split())

            try:
                ctype, cdata = self.parse_command(command_trimmed)

                if ctype == commands.UNKNOWN and not return_anything:
                    # If caller asked for a specifc command and no known command was found
                    raise CommandException("Command not recognized")

            except CommandException as e:
                log(error.BAD_CMD)
                continue
            
            except SyntaxException as e:
                log(error.BAD_SYNTAX)
                continue

            if return_anything: 
                # If the caller will accept anything.
                if ctype == commands.UNKNOWN: 
                    # RETURN whitespace-preserved command IF command type is unknown
                    return ctype, command 
                else: 
                    # RETURN whitespace-stripped command IF cmd was recognized
                    return ctype, cdata 
            else: 
                # Caller asked for specific commands.
                if ctype in command_list: 
                    # Correct formed command found.  Return
                    return ctype, cdata
                else: 
                    # Caller did not get any specified command
                    log(error.BAD_ORDER)
                    continue


    def parse_command(self, cmd):
        """
        See if the command was valid, and return whatever data might have been in the command.
        :param cmd: the command to parse
        :returns: (type, data)
        """

        if cmd.lower().startswith(commands.RCPT_TO.lower()):
            # RCPT TO
            return commands.RCPT_TO, parse_mailbox_cmd(commands.RCPT_TO, cmd)

        elif cmd.lower().startswith(commands.MAIL_FROM.lower()):
            # MAIL FROM
            return commands.MAIL_FROM, parse_mailbox_cmd(commands.MAIL_FROM, cmd)

        elif cmd.lower().startswith(commands.DATA.lower()):
            # DATA
            try:
                assert(commands.check_equal(cmd.rstrip(), commands.DATA))
                return commands.DATA, None
            except:
                raise SyntaxException("DATA command malformed")

        elif cmd.startswith(commands.CLIENT_FROM):
            # From:
            return commands.CLIENT_FROM, parse_mailbox_cmd(commands.CLIENT_FROM, cmd)

        elif cmd.startswith(commands.CLIENT_TO):
            # To:
            return commands.CLIENT_TO, parse_mailbox_cmd(commands.CLIENT_TO, cmd)

        elif cmd.lower().startswith(success.OK_CODE.lower()):
            # 250
            return success.OK_CODE, cmd

        elif cmd.lower().startswith(success.START_DATA_CODE.lower()):
            # 354
            return success.START_DATA_CODE, cmd

        elif re.match(r'^\d\d\d', cmd):
            # DDD
            # Match a three digit number, and return that number as the status
            return cmd[:3], cmd

        else:
            # Something else
            return commands.UNKNOWN, cmd

    def read_line(self):
        command = sys.stdin.readline()

        if command == '':  # EOF Read
            sys.exit(0)

        # Remove the newline
        command = command[:-1]

        return command

    def read_file(self):
        if self.inf:
            line = self.inf.readline()
            if line:
                if '\n' in line:
                    return line[:-1]
                else:
                    return line
            else:
                return None
        else:
            self.inf = open(self.input_filename, 'r')
            return self.read_data()

# -----------------
# Client State Machine Logic
# -----------------

class SMTPClientStateMachine(SMTPStateMachine):
    """
    State Machine:
        START -> enter mail from  <-----+
        -> enter mail to                |
        -> enter mail to or data        |
        -> enter read data  ------------+ 
    """
    
    def enter_mail_from(self, next_mailbox=None):

        if next_mailbox:
            command_type = commands.CLIENT_FROM
            mailbox = next_mailbox
        else:
            command_type, mailbox = self.wait_for([commands.CLIENT_FROM], fromfile=True)
        
        self.emit_from(mailbox)
        self.wait_for_status(success.OK_CODE)

        self.enter_mail_to()

    def enter_mail_to(self):
        
        command_type, mailbox = self.wait_for([commands.CLIENT_TO], fromfile=True)
        self.emit_to(mailbox)
        self.wait_for_status(success.OK_CODE)

        self.enter_mail_to_or_body()

    def enter_mail_to_or_body(self):

        command_type, mailbox = self.wait_for([], fromfile=True)

        while command_type == commands.CLIENT_TO:
            self.emit_to(mailbox)
            self.wait_for_status(success.OK_CODE)

            try:
                command_type, mailbox = self.wait_for([], fromfile=True)
            except:
                break

        # mailbox is now the first line of data!
        self.enter_read_body(mailbox, command_type)

    def enter_read_body(self, first_line, first_type):

        done = False

        # WRITE DATA CMD
        log(commands.DATA)

        # WAIT FOR BEGIN DATA
        self.wait_for_status(success.START_DATA_CODE)

        # ALREADY HAVE FIRST DATA LINE
        data = first_line
        data_type = first_type

        # READ EACH LINE OF DATA, and SEND IT
        while not ( data_type == commands.CLIENT_FROM ) and data:
            log(data) # Strip the newline

            try:
                data = self.read_file()
                data_type, data = self.parse_command(data)
            except:
                done = True
                break

        if not data:
            done = True

        # END WRITE DATA WITH A PERIOD
        log(commands.END_DATA)

        # LISTEN FOR OK
        self.wait_for_status(success.OK_CODE)

        if not done and data_type == commands.CLIENT_FROM:
            # BEGIN CYCLE AGAIN
            self.enter_mail_from(next_mailbox=data)

        else:
            log(commands.QUIT)
            self.inf.close()


    def emit_from(self, mailbox):
        log("{from_cmd} <{mailbox}>".format(
            from_cmd = commands.MAIL_FROM,
            mailbox = mailbox))

    def emit_to(self, mailbox):
        log("{to_cmd} <{mailbox}>".format(
            to_cmd = commands.RCPT_TO,
            mailbox = mailbox)) 

    def wait_for_status(self, status):
        """
        Terminate if something else is received.
        """
        response_type, response = self.wait_for([])
        if response_type == status:
            log(response, stderr=True)
        else:
            #handle bad response type
            log(response, stderr=True)
            log(commands.QUIT)
            sys.exit(1)     

# -----------------
# Server State Machine Logic
# -----------------

class SMTPServerStateMachine(SMTPStateMachine):
    """
    State Machine:
        enter mail from    <------------+
        -> enter rcpt to                |
        -> enter rcpt to or data        |
        -> enter read data              | 
        -> enter finish processing -----+
    """

    def enter_mail_from(self):
        
        command_type, mailbox = self.wait_for( [ commands.MAIL_FROM ] )
        self.mail_from = mailbox
        log(success.OK)
        self.enter_rcpt_to()

    def enter_rcpt_to(self):
        
        command_type, mailbox = self.wait_for( [commands.RCPT_TO] )
        self.to_list.append(mailbox)
        log(success.OK)
        self.enter_rcpt_to_or_data()

    def enter_rcpt_to_or_data(self):
        
        command_type, mailbox = self.wait_for( [commands.RCPT_TO, commands.DATA] )

        while command_type == commands.RCPT_TO:

            self.to_list.append(mailbox)
            log(success.OK)
            command_type, mailbox = self.wait_for( [commands.RCPT_TO, commands.DATA] )

        log(success.START_DATA)
        self.enter_read_data()

    def enter_read_data(self):
        
        data = self.read_line()

        while data != commands.END_DATA:
            self.data_list.append(data)
            print(data)
            data = self.read_line()

        # END read
        log(data) # Will be a period
        log(success.OK)
        
        self.enter_finish_processing()

    def enter_finish_processing(self):

        for recipient in self.to_list:

            with open("./forward/{recipient}".format(
                    recipient=recipient), "a+") as outfile:

                mail = "From: <{mail_from}>\n".format(
                    mail_from=self.mail_from)

                for mailto in self.to_list:
                    mail += "To: <{to}>\n".format(
                        to=mailto)

                for line in self.data_list:
                    mail += line + '\n'

                outfile.write(mail)

# -----------------
# Main Entry Points
# -----------------

def get_args():
    """
    Create an argument parser.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs='?', help="A mail file to read and relay.",  type=argparse.FileType('r'))
    args = parser.parse_args()
    return args

def relay(file):
    """
    Run an SMTP client that opens files, and outputs the associated SMTP commands to a server.
    """
    smtpcsm = SMTPClientStateMachine()
    smtpcsm.inf = file
    smtpcsm.mode = "client"
    smtpcsm.enter_mail_from()

def serve():
    """
    Run an SMTP Server that accepts commands and generates files in the forward directory.
    """
    while True:
        smtpssm = SMTPServerStateMachine()
        smtpssm.mode = "server"
        smtpssm.enter_mail_from()


if __name__ == "__main__":

    args = get_args()

    if args.file:
        relay(args.file)
    else:
        serve()