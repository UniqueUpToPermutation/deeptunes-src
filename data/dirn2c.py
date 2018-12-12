'''
Convert an entire directory of Clara text files into src/target pairs

Usage: python dirn2c.py [src_directory] [result_directory]

src_directory: the path of directory tree to process into src/target pairs
target_directory: the path of the directory (to be created) where the resulting src/target pairs will be written to
'''

import word2chord
import sys

if len(sys.argv) < 3:
    print('Incorrect number of parameters!')
    exit(-1)

src_directory = sys.argv[1]
result_directory = sys.argv[2]

# The length of sequences
extract_length = 12 * 4 * 3
# The length of bins for chords
bin_length = 12

word2chord.dir_converter(src_directory, result_directory, extract_length, bin_length)