import logging
import psycopg2
from collections import deque
from itertools import islice
from threading import Lock
from typing import Deque, List, Optional


class OutputHandler:

    def __init__(self, lock=Lock()):
        self.output_count = 0
        self.lock = lock

    def __call__(self, *args, **kwargs):
        self.output(*args, **kwargs)

    def output(self, *args, **kwargs):
        """Do not override this unless you implement thread safety yourself."""
        self.lock.acquire()
        self.output_count += 1
        self.do_output(*args, **kwargs)
        self.lock.release()

    def do_output(self, *args, **kwargs):
        """Handle the actual output. 
        
        Override this method to create a custom OutputHandler.
        """
        print(f"[Debug] Not Outputting {args}  {kwargs}")

    def done(self):
        """Called just before exiting"""
        pass


class PrintHandler(OutputHandler):

    lock = Lock()
    def __init__(self,
                 scope_name=None,
                 output_formatter=lambda args: ", ".join(args),
                 arg_formatter=lambda arg: str(arg),
                 show_count=False,
                 *print_args,
                 **print_kwargs
                 ):
        self.scope_name = scope_name
        self.output_formatter = output_formatter
        self.arg_formatter = arg_formatter
        self.show_count = show_count
        self.print_args = print_args
        self.print_kwargs = print_kwargs
        super().__init__(PrintHandler.lock)

    def do_output(self, *args):
        formatted_args = [self.arg_formatter(arg) for arg in args]
        output = ""
        if self.show_count or self.scope_name is not None:
            header_parts = []
            if self.scope_name is not None:
                header_parts.append(self.scope_name)
            if self.show_count:
                header_parts.append(f"{self.output_count}")
            header = " ".join(header_parts)
            output += f"[{header}] "

        output += self.output_formatter(formatted_args)
        print(output, *self.print_args, **self.print_kwargs)


class PostgresHandler(OutputHandler):

    def __init__(self,
                 username: str,
                 password: str,
                 database: str,
                 table: str,
                 host: str = "localhost",
                 port: int = 5432,
                 querytemplate: str = "INSERT INTO {table} ({fields}) VALUES ({types})",
                 fieldnames: List[str] = ["username", "password"],
                 fieldtypes: Optional[List[str]] = None,
                 autocommit: bool = False,
                 commitfreq: int = None):

                self.conn = psycopg2.connect(user=username, 
                                             password=password, 
                                             dbname=database,
                                             host=host, 
                                             port=port)
                self.conn.set_session(autocommit=autocommit)
                self.autocommit = autocommit
                self.cursor = self.conn.cursor()
                self.table = table
                self.querytemplate = querytemplate
                self.fieldnames = fieldnames
                self.fieldtypes = fieldtypes if fieldtypes is not None else ["%s"] * len(self.fieldnames)
                self.commitfreq = commitfreq
                self.uncommitted = 0
                self.history = deque([], (self.commitfreq or 1000) * 2)
                self.prep_query()
                super().__init__()

    def prep_query(self):
        fields = ",".join(self.fieldnames)
        types = ",".join(self.fieldtypes)
        self.query = self.querytemplate.format(table=self.table, 
                                          fields=fields, 
                                          types=types)


    def do_output(self, *args):
        try:
            params = args[0]
            self.cursor.execute(self.query, params)
            self.history.append(params)
        except psycopg2.Error  as e:
            logging.debug(f"Caught Error: {e}")
            if not self.autocommit:
                self.retry(self.uncommitted)
            return
        except UnicodeDecodeError as e:
            print(f"{args[0]}")
            logging.error(e)

        self.uncommitted += 1
        self.check_commit()
    
    def do_commit(self):
        logging.debug(f"Committing Transaction")
        try:
            self.conn.commit()
        except psycopg2.Error as e:
            logging.debug(f"Caught Error on Commit: {e}")

    def check_commit(self):
        if self.commitfreq is not None and self.uncommitted >= self.commitfreq:
            self.do_commit()
            self.uncommitted = 0
    
    def rollback(self):
        logging.debug("Rolling Back Changes")
        self.conn.rollback()

    def retry(self, lastn):
        if lastn == 0:
            return
        self.rollback()
        logging.info(f"Retrying last {lastn} queries.")
        last_hist = islice(self.history, len(self.history) - lastn, len(self.history))
        for params in last_hist:
            try:
                self.cursor.execute(self.query, params)
                self.conn.commit()
                self.uncommitted = 0
            except psycopg2.Error as e:
                logging.debug(f"Failed retry of params: {params}. Not Retrying.\n{e}")
            

        
    def done(self):
        logging.info(f"Exiting Postgres Handler")
        self.do_commit()
        self.cursor.close()
        self.conn.close()



