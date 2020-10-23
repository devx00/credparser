from enum import auto
from CredentialParser.CredentialParser import ParsingMode
import time
from argparse import ArgumentParser
from CredentialParser import CredentialParser, PostgresHandler
import signal
import logging

caught_signal = False


def parse_arguments():
    parser = ArgumentParser("CredentialParser")
    parser.add_argument("-d", "--db", help="Database Name")
    parser.add_argument("-t", "--table", help="Table name to use.")
    parser.add_argument("-u", "--username", help="Username to connect to db")
    parser.add_argument("-p", "--password", help="Password to connect to db")
    parser.add_argument("--host", default="localhost", help="Host to connect to")
    parser.add_argument("--port", default=5432, help="Port to connect to.")
    parser.add_argument("-s", "--delimeters", nargs="+", metavar="DELIM", default=[":",";"], help="Delimeters used to split credentials.")
    parser.add_argument("-m", "--mode", default="FIRST_FOUND", choices=["FIRST_FOUND", "LOWEST_INDEX"], help="The strategy used to determine the proper delimeter to use for each value.")
    parser.add_argument("-f", "--fields", nargs="+", metavar="FIELD", default=["username", "password"], help="The field names to use when inserting data into the database.")
    parser.add_argument("--commit-freq", type=int, default=1000, help="The frequency (in number of writes) to commit the new data to the database. (specifying --autocommit renders this value useless)")
    parser.add_argument("--autocommit", action="store_true", default=False, help="Whether to autocommit every database write immediately instead of staging them first. (This can get noisy and I do not know how it will effect performance)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Display verbose output. More = more vewbose." )
    parser.add_argument("files", nargs="+", metavar="FILE", help="The files to parse.")
    return parser.parse_args()


def progress():
    while len(CredentialParser.active_threads()) > 0:
        statuses = [f"[{str(x)}]" for x in CredentialParser.threads]
        print(" ".join(statuses), end="\r")
        time.sleep(1)


def sighandler(signum, frame):
    global caught_signal
    if caught_signal:
        CredentialParser.stop = True
    else:
        caught_signal = True
    print(f"Caught interrupt... Press it again to exit.")
    time.sleep(5)

def set_logging(level=0):
    loglevel = logging.WARNING
    if level > 0:
        loglevel = (logging.DEBUG if level >= 3 
                    else logging.INFO if level >= 2 
                    else logging.WARNING)
    logging.basicConfig(level=loglevel)


def main():
    signal.signal(signal.SIGINT, sighandler)
    args = parse_arguments()
    set_logging(level=args.verbose)
    handler = PostgresHandler(username=args.username,
                              password=args.password,
                              database=args.db,
                              table=args.table,
                              fieldnames=args.fields,
                              host=args.host,
                              port=args.port,
                              commitfreq=args.commit_freq,
                              autocommit=args.autocommit)
    for f in args.files:
        c = CredentialParser(f, output_handler=handler, parse_mode=ParsingMode.mode_for_str(args.mode), delimiters=args.delimeters)
        c.start()
    progress()
    


if __name__ == "__main__":
    main()
