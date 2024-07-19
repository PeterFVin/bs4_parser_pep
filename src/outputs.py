import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import BASE_DIR, DATETIME_FORMAT

CONTROL_OUTPUT_PRETTY = 'pretty'
CONTROL_OUTPUT_FILE = 'file'
FILE_OUTPUT = 'Файл с результатами был сохранён: {}'
RESULTS_DIR = BASE_DIR / 'results'


def control_output(results, cli_args):
    outputs[cli_args.output](results, cli_args)


def default_output(results, cli_args):
    for row in results:
        print(*row)


def pretty_output(results, cli_args):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    RESULTS_DIR.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now_formatted = dt.datetime.now().strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = RESULTS_DIR / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        csv.writer(f, dialect=csv.unix_dialect).writerows(results)
    logging.info(FILE_OUTPUT.format(file_path))


outputs = {
    CONTROL_OUTPUT_PRETTY: lambda results, cli_args: pretty_output(results,
                                                                   cli_args),
    CONTROL_OUTPUT_FILE: lambda results, cli_args: file_output(results,
                                                               cli_args),
    None: lambda results, cli_args: default_output(results, cli_args)
}
