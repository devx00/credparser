from threading import Lock
from typing import List, Optional
import psycopg2

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
                 autocommit: bool = False):

                self.conn = psycopg2.connect(user=username, 
                                             password=password, 
                                             dbname=database,
                                             host=host, 
                                             port=port)
                self.cursor = self.conn.cursor()
                self.table = table
                self.querytemplate = querytemplate
                self.fieldnames = fieldnames
                self.fieldtypes = fieldtypes if fieldtypes is not None else ["%s"] * len(self.fieldnames)
                self.autocommit = autocommit
                super().__init__()


    def do_output(self, *args):
        fields = ",".join(self.fieldnames)
        types = ",".join(self.fieldtypes)
        query = self.querytemplate.format(table=self.table, 
                                          fields=fields, 
                                          types=types)
        self.cursor.execute(query, *args)
        if self.autocommit:
            self.conn.commit()
    
    def done(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()



