from CredentialParser.util import str_index
from threading import Thread
from enum import Enum
from typing import Iterable, List, Optional

from CredentialParser.OutputHandler import OutputHandler, PrintHandler

class ParsingMode(Enum):
    FIRST_FOUND = 1
    """Tries each delimeter until one exists in the input"""

    LOWEST_INDEX = 2
    """Checks for all the delimeters and parses at the lowest index found"""

class CredentialParser(Thread):

    stop = False
    
    def __init__(self,
                 inputs: Iterable[str],
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
        self.inputs = inputs
        self.delimeters = delimiters
        self.num_values = num_values
        self.parse_mode = parse_mode
        self.output_handler = output_handler
        self.error_handler = error_handler
        super().__init__()

    def cleanup(self):
        """Called just before exiting."""
        self.output_handler.done()
        self.error_handler.done()


    def run(self):
        for val in self.inputs:
            if self.stop:
                break
            val = val.strip()
            self.parse(val)
        self.cleanup()
    
    def get_delimeter(self, val) -> Optional[str]:
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
        self.output_handler(vals)
        