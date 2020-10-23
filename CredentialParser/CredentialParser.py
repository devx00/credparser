from argparse import FileType
from CredentialParser.util import str_index
from threading import Thread
from enum import Enum
from typing import Any, IO, Iterable, List, Optional
from datetime import datetime, timedelta
from CredentialParser.OutputHandler import OutputHandler, PrintHandler

class ParsingMode(Enum):
    FIRST_FOUND = 1
    """Tries each delimeter until one exists in the input"""

    LOWEST_INDEX = 2
    """Checks for all the delimeters and parses at the lowest index found"""

    @classmethod
    def mode_for_str(cls, modestr):
        if modestr.lower() == "lowest_index":
            return ParsingMode.LOWEST_INDEX
        else:
            return ParsingMode.FIRST_FOUND


class CredentialParser(Thread):

    stop = False
    threads: List[Thread] = []

    @classmethod
    def active_threads(cls):
        return [t for t in CredentialParser.threads if t.is_alive() and isinstance(t, CredentialParser)]

    def __init__(self,
                 filename: str,
                 delimiters: List[str]=[":", ";"],
                 num_values: int = 2,
                 parse_mode: ParsingMode = ParsingMode.FIRST_FOUND,
                 output_handler: OutputHandler = PrintHandler(
                                                    scope_name="Output",
                                                    show_count=True
                                                ),
                 error_handler: OutputHandler = PrintHandler(
                                                        scope_name="Error", 
                                                        show_count=True
                                                        )
                 ):
        self.filename = filename
        self.delimeters = [d.encode() for d in delimiters]
        self.num_values = num_values
        self.parse_mode = parse_mode
        self.output_handler = output_handler
        self.error_handler = error_handler
        self.input_count = 0
        self.processed_count = 0
        super().__init__()
        self.starttime = None
        CredentialParser.threads.append(self)
        self.get_input_count()

    def __str__(self):
        return f"{self.filename}: {self.progress} | {self.percent_complete:.02f}%"

    @property
    def runtime(self) -> timedelta:
        if self.starttime is None:
            return timedelta(seconds=0)
        return datetime.now() - self.starttime

    @property
    def percent_complete(self):
        return self.processed_count / self.input_count * 100

    @property
    def progress(self):
        return f"{self.processed_count}/{self.input_count}"

    def cleanup(self):
        """Called just before exiting."""
        self.output_handler.done()
        self.error_handler.done()

    def get_input_count(self):
        self.input_count = len(open(self.filename, 'rb').readlines())

    def run(self):
        self.starttime = datetime.now()
        for val in open(self.filename, "rb"):
            if self.stop:
                break
            val = val.strip()
            self.parse(val)
            self.processed_count += 1
        self.cleanup()
    
    def get_delimeter(self, val) -> Optional[bytes]:
        if self.parse_mode == ParsingMode.FIRST_FOUND:
            for d in self.delimeters:
                if d in val:
                    return d
        elif self.parse_mode == ParsingMode.LOWEST_INDEX:
            delim = None
            delim_ind = None
            for d in self.delimeters:
                ind = str_index(val, d)
                if ind is not None and (delim_ind is None or ind < delim_ind):
                    delim = d
                    delim_ind = ind
            return delim

    def parse(self, val):
        delim = self.get_delimeter(val)
        if delim is None:
            self.error_handler(f"Couldn't determine delimeter.", val)
            return
        
        vals = val.split(delim)
        vals = vals[:self.num_values - 1] + [delim.join(vals[self.num_values - 1:])]
        vals = self.attempt_decode(vals)
        self.output_handler(vals)

    def attempt_decode(self, vals):
        encodings = ['utf8', 'latin-1']
        for enc in encodings:
            try:
                utfvals = [x.decode(enc) for x in vals]
                if enc != "utf8":
                    utfvals = [x.encode('utf8').decode('utf8') for x in utfvals]
                return utfvals
            except UnicodeDecodeError:
                pass
        return vals
        