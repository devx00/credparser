from CredentialParser.OutputHandler import LoggingHandler, FileHandler
from enum import auto
from CredentialParser.CredentialParser import ParsingMode
import time
from argparse import ArgumentParser
from CredentialParser import CredentialParser, PostgresHandler
import signal
import logging
from pathlib import Path
caught_signal = False


def parse_arguments():
    parser = ArgumentParser("CredentialParser")
    parser.add_argument("-s", "--delimeters", nargs="+", metavar="DELIM", default=[":",";"], help="Delimeters used to split credentials.")
    parser.add_argument("-m", "--mode", default="FIRST_FOUND", choices=["FIRST_FOUND", "LOWEST_INDEX"], help="The strategy used to determine the proper delimeter to use for each value.")
    parser.add_argument("files", nargs="+", metavar="FILE", help="The files to parse.")
    parser.add_argument("-o", "--output-mode", choices=["file", "postgres"], default="file", help="The output mode to use.")
    parser.add_argument("--refresh-time", default=1, help="The refresh frequency for the progress text.")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Display verbose output. More = more vewbose." )
    file_args = parser.add_argument_group("File Output")
    file_args.add_argument("-r", "--replacement-delimiter", default="\t", help="The new delimiter to use when writing to the new file.")
    file_args.add_argument("-O", "--output-suffix", default="_sanitized", help="The output suffix to add to each filename. SO if you input passfile1.txt and passfile2.txt then their output files would be passfile1_sanitized.txt and passfile2_sanitized.txt if the suffix is '_sanitized'.")
    file_args.add_argument("-M", "--file-mode", default="w", choices=['w', 'a'], help="The mode to use when opening the file object. Default: 'w'")
    file_args.add_argument("-D", "--directory", default=".", help="The directory to use for the output files.")
    pg_parser = parser.add_argument_group("Postgres")
    pg_parser.add_argument("-d", "--db", help="Database Name")
    pg_parser.add_argument("-t", "--table", help="Table name to use.")
    pg_parser.add_argument("-u", "--username", help="Username to connect to db")
    pg_parser.add_argument("-p", "--password", help="Password to connect to db")
    pg_parser.add_argument("--host", default="localhost", help="Host to connect to")
    pg_parser.add_argument("--port", default=5432, help="Port to connect to.")
    pg_parser.add_argument("-f", "--fields", nargs="+", metavar="FIELD", default=["username", "password"], help="The field names to use when inserting data into the database.")
    pg_parser.add_argument("--commit-freq", type=int, default=1000, help="The frequency (in number of writes) to commit the new data to the database. (specifying --autocommit renders this value useless)")
    pg_parser.add_argument("--autocommit", action="store_true", default=False, help="Whether to autocommit every database write immediately instead of staging them first. (This can get noisy and I do not know how it will effect performance)")
    return parser.parse_args()


def progress(refresh_freq=1):
    last_len = 0
    def blank():
        print(" " * last_len, end="\r")
    while len(CredentialParser.active_threads()) > 0:
        statuses = [f"[{str(x)}]" for x in CredentialParser.active_threads()]
        joined_statuses = " ".join(statuses)
        blank()
        print(joined_statuses, end="\r")
        last_len = len(joined_statuses)
        time.sleep(refresh_freq)
    blank()

def thread_completed(thread: CredentialParser):
    print(f"{thread.filename} finished in {thread.natural_runtime}.")

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

def get_file_handler(args, filepath):
    filepath = Path(filepath)
    fileext = filepath.suffix
    filename = filepath.stem
    outdir = Path(args.directory)
    outfile = Path(f"{filename}{args.output_suffix}{fileext}")
    outpath = outdir.joinpath(outfile)
    return FileHandler(outpath, filemode=args.file_mode, delimiter=args.replacement_delimiter)

def get_postgres_handler(args):
    return PostgresHandler(username=args.username,
                           password=args.password,
                           database=args.db,
                           table=args.table,
                           fieldnames=args.fields,
                           host=args.host,
                           port=args.port,
                           commitfreq=args.commit_freq,
                           autocommit=args.autocommit)


def main():
    signal.signal(signal.SIGINT, sighandler)
    args = parse_arguments()
    set_logging(level=args.verbose)
    
    err_handler = LoggingHandler("Debug", log_level=logging.DEBUG)
    for f in args.files:
        handler = get_postgres_handler(
            args) if args.output_mode == "postgres" else get_file_handler(args, f)
        c = CredentialParser(f, output_handler=handler, parse_mode=ParsingMode.mode_for_str(args.mode), delimiters=args.delimeters, error_handler=err_handler, completion_handler=thread_completed)
        c.start()
    progress()
    


if __name__ == "__main__":
    main()
