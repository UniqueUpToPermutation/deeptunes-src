'''
Convert a single file into src/target pairs

Usage: python n2c.py [input_file] [output_file_src] [output_file_target]

[input_file] : The input Clara file
[output_file_src] : The src processed Clara file
[output_file_target] : The output target file, with the chord representation of the input Clara file
'''

import word2chord
import sys

if len(sys.argv) < 4:
    print('Incorrect number of parameters!')
    exit(-1)

input = sys.argv[1]
output_src = sys.argv[2]
output_target = sys.argv[3]

# The length of sequences
extract_length = 12 * 4 * 3
# The length of bins for chords
bin_length = 12

word2chord.file_converter(input, output_src, output_target, extract_length, bin_length)