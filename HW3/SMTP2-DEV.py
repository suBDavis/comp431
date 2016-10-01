#!/usr/bin/python

# -----------------
# Comp431
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

class CommandException(Exception):
    pass

class SyntaxException(Exception):
    pass

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
        # if stderr:
        #     print(string, file=sys.stderr)
        # else:   
        #     print(string)
        pass
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

def parse_code(line):
    pass


# -----------------
# Parent State Machine Logic
# -----------------

class SMTPStateMachine:

    def __init__(self):
        self.input_file = None
        self.to_list = []
        self.mail_from = None
        self.data_list = []

    def wait_for(self, command_list, source=None):
        """
        Waits in a loop for the specified list of commands.
        If the list is empty, return anything.
        """

        return_anything = len(command_list) < 1

        while True:
            
            command = self.read_line()
            
            print(command)

            # Replace all whitespace runs with a single space
            command_trimmed = ' '.join(command.split())

            try:
                ctype, cdata = self.parse_command(command_trimmed)

                if ctype == commands.UNKNOWN and not return_anything:
                    raise CommandException("Command not recognized")

            except CommandException as e:
                log(error.BAD_CMD)
                continue
            
            except SyntaxException as e:
                log(error.BAD_SYNTAX)
                continue

            if return_anything:
                if ctype == commands.UNKNOWN:
                    return ctype, command
                else:
                    return ctype, cdata
            else:         
                if ctype in command_list:
                    return ctype, cdata
                else:
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
            try:
                assert(commands.check_equal(cmd.rstrip(), commands.DATA))
                return commands.DATA, None
            except:
                raise SyntaxException("DATA command malformed")

        elif cmd.startswith(commands.CLIENT_FROM):
            return commands.CLIENT_FROM, parse_mailbox_cmd(commands.CLIENT_FROM, cmd)

        elif cmd.startswith(commands.CLIENT_TO):
            return commands.CLIENT_TO, parse_mailbox_cmd(commands.CLIENT_TO, cmd)

        elif cmd.lower().startswith(success.OK_CODE.lower()):
            return success.OK_CODE, cmd

        elif cmd.lower().startswith(success.START_DATA_CODE.lower()):
            return success.START_DATA_CODE, cmd

        elif re.match(r'^\d\d\d', cmd):
            #Match a three digit number.
            return cmd[:3], cmd

        else:
            return commands.UNKNOWN, cmd

    def read_line(self):

        if self.input_file:
            pass
        else:
            command = sys.stdin.readline()

        if command == '':  # EOF Read
            sys.exit(0)

        # Remove the newline
        command = command[:-1]

        return command

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
    
    def enter_mail_from(self, first_from=None):

        if first_from:
            command_type = commands.CLIENT_FROM
            mailbox = parse_mailbox_cmd(command_type, first_from)
        else:
            command_type, mailbox = self.wait_for([commands.CLIENT_FROM])
        
        self.mail_from = mailbox
        self.emit_from(mailbox)
        self.wait_for_OK()

        self.enter_mail_to()

    def enter_mail_to(self):
        
        command_type, mailbox = self.wait_for([commands.CLIENT_TO])
        self.to_list.append(mailbox)
        self.emit_to(mailbox)
        self.wait_for_OK()

        self.enter_mail_to_or_body()

    def enter_mail_to_or_body(self):
        
        command_type, mailbox = self.wait_for([])

        while command_type == commands.CLIENT_TO:

            self.to_list.append(mailbox)
            self.emit_to(mailbox)
            self.wait_for_OK()

            command_type, mailbox = self.wait_for([])

        # mailbox is now the first line of data!
        # verify mailbox is also not NULL or another "From"

        if not command_type == commands.CLIENT_FROM \
            and not mailbox == None:

            self.enter_read_body(mailbox)

        else:
            log(mailbox, stderr=True)
            log(commands.QUIT)
            sys.exit(1)

    def enter_read_body(self, first_line):

        # WRITE DATA CMD
        log(commands.DATA)

        # WAIT FOR OK TO BEGIN DATA
        response_type, response = self.wait_for([])
        if response_type == success.START_DATA_CODE:
            log(response, stderr=True)
        else:
            log(response, stderr=True)
            log(commands.QUIT)
            sys.exit(1)

        # ALREADY HAVE FIRST DATA LINE
        data = first_line
        data_type = commands.UNKNOWN

        # READ EACH LINE OF DATA, and SEND IT
        while data_type == commands.UNKNOWN:
            self.data_list.append(data)
            print(data)
            data_type, data = self.wait_for([])

        # END WRITE DATA WITH A PERIOD
        log(commands.END_DATA)

        # LISTEN FOR ACK
        self.wait_for_OK()

        # BEGIN CYCLE AGAIN
        self.enter_mail_from(first_from=data)


    def emit_from(self, mailbox):
        log("{from_cmd} <{mailbox}>".format(
            from_cmd = commands.MAIL_FROM,
            mailbox = mailbox))

    def emit_to(self, mailbox):
        log("{to_cmd} <{mailbox}>".format(
            to_cmd = commands.RCPT_TO,
            mailbox = mailbox)) 

    def wait_for_OK(self):
        """
        Returns 1 if OK received.
        Otherwise, terminates
        """
        response_type, response = self.wait_for([])
        if response_type == success.OK_CODE:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='?', help="A mail file to read and relay.")
    args = parser.parse_args()
    return args

def relay(file_list):
    """
    Run an SMTP client that opens files, and outputs the associated SMTP commands to a server.
    """
    smtpcsm = SMTPClientStateMachine()
    smtpcsm.enter_mail_from()

def serve():
    """
    Run an SMTP Server that accepts commands and generates files in the forward directory.
    """
    while True:
        smtpssm = SMTPServerStateMachine()
        smtpssm.enter_mail_from()


if __name__ == "__main__":

    args = get_args()

    if args.files:
        relay(args.files)
    else:
        serve()