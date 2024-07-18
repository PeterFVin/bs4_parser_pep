from pathlib import Path

MAIN_DOC_URL = 'https://docs.python.org/3/'
MAIN_PEP_URL = 'https://peps.python.org/'

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'parser.log'
OUTPUT_PRETTY = 'pretty'
OUTPUT_FILE = 'file'
RESULTS_DIR = BASE_DIR / 'results'

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred'),
    'F': ('Final'),
    'P': ('Provisional'),
    'R': ('Rejected'),
    'S': ('Superseded'),
    'W': ('Withdrawn'),
    '': ('Draft', 'Active'),
}
