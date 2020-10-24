from argparse import FileType
from CredentialParser.util import str_index, timestr
from threading import Thread
from enum import Enum
from typing import Any, Callable, IO, Iterable, List, Optional
from datetime import datetime, timedelta
from CredentialParser.OutputHandler import LoggingHandler, OutputHandler, PrintHandler
import humanize

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
    threads: List['CredentialParser'] = []

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
                 error_handler: OutputHandler = LoggingHandler(
                                                        scope_name="Debug", 
                                                        show_count=True
                                                        ),
                 completion_handler: Callable = None
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
        self.endtime = None
        CredentialParser.threads.append(self)
        self.output_handler.attach()
        self.error_handler.attach()
        self.input_count = 0
        self.completion_handler = completion_handler
        self.state = "initialized"

    def __str__(self):
        if self.state == "finished":
            return f"{self.filename}: Finished in {humanize.naturaldelta(self.runtime)}"
        if self.state == "loading" or self.state == "initialized":
            return f"{self.filename}: loading"
        return f"{self.filename}: {self.percent_complete:.02f}% | {self.natural_eta} left | {self.natural_runtime} elapsed"

    @property
    def runtime(self) -> timedelta:
        if self.starttime is None:
            return timedelta(seconds=0)
        endtime = self.endtime or datetime.now()
        return endtime - self.starttime

    @property
    def natural_runtime(self):
        return timestr(self.runtime)

    @property
    def percent_complete(self):
        return self.processed_count / self.input_count * 100

    @property
    def progress(self):
        return f"{self.processed_count}/{self.input_count}"

    @property
    def speed(self):
        return self.processed_count / self.runtime.total_seconds()

    @property
    def eta(self):
        if self.speed == 0:
            return timedelta(seconds=0)
        left = self.input_count - self.processed_count
        return timedelta(seconds=left/self.speed)

    @property
    def natural_eta(self):
        return timestr(self.eta)

    def cleanup(self):
        """Called just before exiting."""
        self.state = "finished"
        self.endtime = datetime.now()
        self.output_handler.detach()
        self.error_handler.detach()
        if self.completion_handler is not None:
            self.completion_handler(self)

    def get_input_count(self):
        self.input_count = len(open(self.filename, 'rb').readlines())

    def run(self):
        self.status = "loading"
        self.get_input_count()
        self.state = "running"
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
            self.error_handler((f"Couldn't determine delimeter.", val))
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
        
