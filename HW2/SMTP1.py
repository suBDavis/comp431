import sys
import re

SPECIAL = ['<', '>', '(', ')', '[', ']', '\\', '.', ',', ';', ':', '@', '"']
WHITESPACE = [' ', '\t']
SP = ' '
AT = '@'

#
# Exception Classes
#

class CommandException(Exception):
    pass

class SyntaxException(Exception):
    pass

class OrderException(Exception):
    pass

#
# Enumerators
#

class commands:
    
    MAIL_FROM = "MAIL FROM:".lower()
    RCPT_TO = "RCPT TO:".lower()
    DATA = "DATA".lower()
    END_DATA = ".".lower()

    @staticmethod
    def check_equal(cmd1, cmd2):
        return cmd1.lower() == cmd2.lower()

class error:

    BAD_CMD = "500 Syntax error: command unrecognized"
    BAD_SYNTAX = "501 Syntax error in parameters or arguments"
    BAD_ORDER = "503 Bad sequence of commands"

class success:

    OK = "250 OK"
    START_DATA = "354 Start mail input; end with <CRLF>.<CRLF>"

#
# Helper functions
#

def log(string):
    print(string)

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


#
# State Machine Logic
#

class SMTPStateMachine:
    """
    State Machine:
        enter mail from    <------------+
        -> enter rcpt to                |
        -> enter rcpt to or data        |
        -> enter read data              | 
        -> enter finish processing -----+
    """

    def __init__(self):
        self.to_list = []
        self.mail_from = None
        self.data_list = []

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

    def wait_for(self, command_list):
        """
        Waits in a loop for the specified list of commands.
        """

        while True:

            command = self.read_line()

            print(command)

            # Replace all whitespace runs with a single space
            command = ' '.join(command.split())

            try:
                ctype, cdata = self.parse_command(command)
            
            except CommandException as e:
                log(error.BAD_CMD)
                continue
            
            except SyntaxException as e:
                log(error.BAD_SYNTAX)
                continue

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

        if cmd.lower().startswith(commands.RCPT_TO):
            # RCPT TO
            return commands.RCPT_TO, parse_mailbox_cmd(commands.RCPT_TO, cmd)

        elif cmd.lower().startswith(commands.MAIL_FROM):
            # MAIL FROM
            return commands.MAIL_FROM, parse_mailbox_cmd(commands.MAIL_FROM, cmd)

        elif cmd.lower().startswith(commands.DATA):
            try:
                assert(commands.check_equal(cmd.rstrip(), commands.DATA))
                return commands.DATA, None
            except:
                raise SyntaxException("DATA command malformed")

        else:
            raise CommandException("Command not recognized")

    def read_line(self):
        
        command = sys.stdin.readline()

        if command == '':  # EOF Read
            sys.exit(0)

        # Remove the newline
        command = command[:-1]

        return command

if __name__ == "__main__":

    while True:
        smtpsm = SMTPStateMachine()
        smtpsm.enter_mail_from()