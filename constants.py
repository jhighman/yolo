import os

# Directory configurations
FOLDER_PATH = './'
INPUT_FOLDER = os.path.join(FOLDER_PATH, 'drop')
OUTPUT_FOLDER = os.path.join(FOLDER_PATH, 'output')
ARCHIVE_FOLDER = os.path.join(FOLDER_PATH, 'archive')
CACHE_FOLDER = os.path.join(FOLDER_PATH, 'cache')
CHECKPOINT_FILE = os.path.join(OUTPUT_FOLDER, 'checkpoint.json')