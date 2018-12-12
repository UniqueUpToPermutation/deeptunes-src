import sys
import enum
import bisect
import copy
import os
import shutil

class Note:
    def __init__(self, begin, length, note_id, b_repeated_before, b_repeated_after):
        self.note_begin = begin
        self.note_length = length
        self.note_id = note_id
        self.b_repeated_after = b_repeated_after
        self.b_repeated_before = b_repeated_before

    def get_note_end(self):
        return self.note_begin + self.note_length

    def get_clara_note_end(self):
        if self.b_repeated:
            return self.note_end
        else:
            return self.note_begin + self.note_length - 1

    note_end = property(get_note_end)
    clara_note_end = property(get_clara_note_end)


class NoteEventType(enum.Enum):
    Begin = 0
    End = 1
    Repeat = 2


class NoteEventData(enum.IntEnum):
    Type = 0
    Note = 1
    Time = 2


class MusicPiece:
    def __init__(self, notes, time_length):
        self.notes = notes

        note_begin_events = [(NoteEventType.Begin, x, x.note_begin) for x in notes]
        note_end_events = [(NoteEventType.End, x, x.note_end) for x in notes]
        self.note_events = note_begin_events + note_end_events
        self.note_events = sorted(self.note_events, key=lambda x: x[NoteEventData.Note].note_id)
        self.note_events = sorted(self.note_events, key=lambda x: x[NoteEventData.Time])
        self.event_times = [x[NoteEventData.Time] for x in self.note_events]

        clara_begin_events = [(NoteEventType.Begin, x, x.note_begin) for x in notes if not x.b_repeated_before]
        clara_end_events = [(NoteEventType.End, x, x.note_end - 1) for x in notes if not x.b_repeated_after]
        clara_repeat_events = [(NoteEventType.Repeat, x, x.note_begin) for x in notes if x.b_repeated_before]
        self.clara_note_events = clara_begin_events + clara_end_events + clara_repeat_events
        self.clara_note_events = sorted(self.clara_note_events, key=lambda x: x[NoteEventData.Note].note_id)
        self.clara_note_events = sorted(self.clara_note_events, key=lambda x: x[NoteEventData.Time])
        self.clara_event_times = [x[NoteEventData.Time] for x in self.clara_note_events]

        self.length = time_length

    # Note that if a note begins and ends outside of the [begin_time, begin_time + length) window, it will not be
    # caught by this algorithm. Perhaps something to fix in the future?
    def sub_piece(self, begin_time, length):
        begin_index = bisect.bisect_left(self.clara_event_times, begin_time)
        end_time = begin_time + length
        end_index = bisect.bisect_left(self.clara_event_times, end_time)

        events = self.clara_note_events[begin_index:end_index] # Get corresponding events
        sub_notes_set = {x[NoteEventData.Note] for x in events} # Get corresponding notes
        sub_notes_copy = [copy.copy(x) for x in sub_notes_set] # Copy notes

        # Alter the time of all the notes
        for note in sub_notes_copy:
            # Shift notes backward in time
            note.note_begin -= begin_time

            # Truncate the beginning of notes
            note_cut_begin = max(-note.note_begin, 0)
            note.note_begin = max(note.note_begin, 0)
            note.note_length -= note_cut_begin

            # Truncate the end of notes
            note_cut_end = max(note.note_begin + note.note_length - length, 0)
            note.note_length -= note_cut_end

            # Eliminate repeats if necessary
            if note.note_begin == 0:
                note.b_repeated_before = False
            if note.note_end == length:
                note.b_repeated_after = False

        time_length = length
        subpiece = MusicPiece(sub_notes_copy, time_length)
        return subpiece

    def to_chord_string(self, bin_length):
        chords = gen_chords_from_piece(self, bin_length)
        chord_strs = [chord_to_string(x) for x in chords]
        chord_strs_joined = ' '.join(chord_strs)
        return chord_strs_joined

    def to_clara_string(self):
        max_wait_time = 25

        current_time = 0
        tolkens = []

        for event in self.clara_note_events:
            event_time = event[NoteEventData.Time]
            event_type = event[NoteEventData.Type]
            event_note = event[NoteEventData.Note]

            while event_time > current_time:
                wait_time = min(max_wait_time, event_time - current_time)
                tolkens.append(f'wait{wait_time}')
                current_time += wait_time

            if event_type == NoteEventType.Begin or event_type == NoteEventType.Repeat:
                note_id = event_note.note_id
                tolkens.append(f'p{note_id}')
            elif event_type == NoteEventType.End:
                note_id = event_note.note_id
                tolkens.append(f'endp{note_id}')

        wait_padding = self.length - current_time
        tolkens.append(f'wait{wait_padding}')

        return ' '.join(tolkens)


def gen_piece_from_data(data):
    notes = []
    active_notes = dict()
    current_time = 0
    for tolken in data:
        if len(tolken) == 0:
            continue
        elif tolken[0] == 'w': #wait token
            wait_length = int(tolken[4:])
            current_time += wait_length #Advance time
        elif tolken[0] == 'p': #note start token

            note_quality = int(tolken[1:])

            # We may have note repeats
            b_repeated_before = False
            if note_quality in active_notes:
                note = active_notes.pop(note_quality)
                note.note_length = current_time - note.note_begin
                note.b_repeated_after = True
                b_repeated_before = True
                notes.append(note)

            note = Note(current_time, 0, note_quality, False, False)
            active_notes[note_quality] = note
        elif tolken[0] == 'e': #note end token
            note_quality = int(tolken[4:])
            note = active_notes.pop(note_quality)
            note.note_length = current_time - note.note_begin + 1
            notes.append(note)
        else:
            print('Warning: incorrect token!')
            assert(False)

    notes = sorted(notes, key=lambda x : x.note_begin) #Sort, just in case
    piece = MusicPiece(notes, current_time)
    return piece


def read_piece_from_string(input_str):
    data = input_str.split(' ')
    piece = gen_piece_from_data(data)
    return piece


def read_piece_from_file_handle(file_handle):
    file_contents = file_handle.read()
    piece = read_piece_from_string(file_contents)
    return piece


def read_piece_from_file(file_name):
    file_handle = open(file_name, "r")
    result = read_piece_from_file_handle(file_handle)
    file_handle.close()
    return result


def gen_chords_from_piece(piece, chord_bin_length):

    class ChordGenerator:
        def __init__(self, piece):
            self.long_term_active_notes = set()
            self.short_term_active_notes = set()
            self.piece = piece

        def on_note_begin(self, event, note):
            self.long_term_active_notes.add(event_note)

        def on_note_end(self, event, note, bin_begin):
            self.long_term_active_notes.remove(event_note)
            # This note was part of the last bin, don't add to short term notes
            if event[NoteEventData.Time] != bin_begin:
                self.short_term_active_notes.add(event_note)

        def consolidate_chord(self):
            active_notes = self.long_term_active_notes | self.short_term_active_notes

            if len(active_notes) > 4:  # If total number of active notes is more than 4, take four longest
                # TODO: Need to fix, might have duplicate notes!
                items = list(active_notes)
                items_sorted = sorted(items, key=lambda x: -x.note_length)
                chord = set(items_sorted[0:4])
            else:
                chord = active_notes

            self.short_term_active_notes = set()

            return chord

    chords = []
    current_bin_start = 0
    current_bin_end = 0

    chord_gen = ChordGenerator(piece)

    for note_event in piece.note_events:

        event_type = note_event[NoteEventData.Type]
        event_note = note_event[NoteEventData.Note]
        event_time = note_event[NoteEventData.Time]

        current_bin_end = current_bin_start + chord_bin_length
        while event_time >= current_bin_end: # We've ended the bin
            chords.append(chord_gen.consolidate_chord())
            current_bin_start += chord_bin_length
            current_bin_end = current_bin_start + chord_bin_length

        # Keep track of "active" notes
        if event_type == NoteEventType.Begin:
            chord_gen.on_note_begin(note_event, event_note)
        elif event_type == NoteEventType.End:
            chord_gen.on_note_end(note_event, event_note, current_bin_start)

    # Cleanup, add any additional chords as necessary
    current_bin_end = current_bin_start + chord_bin_length
    while current_bin_end <= piece.length:
        chords.append(chord_gen.consolidate_chord())
        current_bin_start += chord_bin_length
        current_bin_end = current_bin_start + chord_bin_length

    return chords


def chord_to_string(chord):
    note_strings = ['A', 'A#/Bb', 'B', 'C', 'C#/Db', 'D',
                    'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab']

    if len(chord) == 0:
        return 'Empty'

    chord_modulo = [(x.note_id - 24 + 36) % 12 for x in chord]
    chord_modulo = sorted(set(chord_modulo))
    chord_strs = [note_strings[x] for x in chord_modulo]
    chord_str = '_'.join(chord_strs)
    return chord_str


def piece_to_src_target_pairs(piece, extract_length, bin_length):
    current_position = 0
    results = []
    src_results = []

    while current_position + extract_length <= piece.length:
        subpiece = piece.sub_piece(current_position, extract_length)
        chord_strs_joined = subpiece.to_chord_string(bin_length)
        clara_strs = subpiece.to_clara_string()
        results.append(chord_strs_joined)
        src_results.append(clara_strs)
        current_position += extract_length

    results_str = '\n'.join(results)
    src_results_str = '\n'.join(src_results)

    return src_results_str, results_str


def split_piece_into_transpositions(piece):
    split_length = int(piece.length / 12)
    return [piece.sub_piece(i * split_length, split_length) for i in range(0, 12)]


def transposed_piece_to_src_target_pairs(piece,  extract_length, bin_length):
    piece_transpositions = split_piece_into_transpositions(piece)
    results_strs = []
    src_results_strs = []
    for transposition in piece_transpositions:
        (src_results_str, results_str) = piece_to_src_target_pairs(piece, extract_length, bin_length)
        results_strs.append(results_str)
        src_results_strs.append(src_results_str)
    results_str = '\n'.join(results_strs)
    src_results_str = '\n'.join(src_results_strs)
    return src_results_str, results_str


def dir_converter(src_path, target_path, extract_length, bin_length):

    # Copy src path directory to target path directory
    if os.path.lexists(target_path):
        shutil.rmtree(target_path)
    shutil.copytree(src_path, target_path)

    # Walk through target path directory
    for root, dirs, files in os.walk(target_path, topdown=False):
        for file in files:
            if file.endswith('.txt'):
                print('Converting ' + file + '...')

                piece_file = os.path.join(root, file)

                piece = read_piece_from_file(piece_file)

                (src_results_str, results_str) = transposed_piece_to_src_target_pairs(piece, extract_length, bin_length)

                file_name_target_target = os.path.join(root, 'src_' + file)
                file_name_target_src = os.path.join(root, 'target_' + file)

                h_results = open(file_name_target_target, 'w')
                h_src_results = open(file_name_target_src, 'w')
                h_results.write(results_str)
                h_src_results.write(src_results_str)
                h_results.close()
                h_src_results.close()

                # Remove target file
                os.remove(piece_file)


def file_converter(input_path, output_path_src, output_path_target, extract_length, bin_length):
    piece_file = input_path

    piece = read_piece_from_file(piece_file)

    (src_results_str, results_str) = transposed_piece_to_src_target_pairs(piece, extract_length, bin_length)

    file_name_target_target = output_path_target
    file_name_target_src = output_path_src

    h_results = open(file_name_target_target, 'w')
    h_src_results = open(file_name_target_src, 'w')
    h_results.write(results_str)
    h_src_results.write(src_results_str)
    h_results.close()
    h_src_results.close()


def main():
    if len(sys.argv) == 0:
        exit(0)

    begin_extract = 0
    extract_length = 12 * 12
    bin_length = 12
    input_file = sys.argv[1]

    piece = read_piece_from_file(input_file)
    results = []
    src_results = []

    piece_transpositions = split_piece_into_transpositions(piece)
    (src_results_str, results_str) = transposed_piece_to_src_target_pairs(piece, extract_length, bin_length)

    print(results_str)
    print(src_results_str)

    h_results = open('target.txt', 'w')
    h_src_results = open('src.txt', 'w')
    h_results.write(results_str)
    h_src_results.write(src_results_str)
    h_results.close()
    h_src_results.close()


def test2():
    s = 'p55 wait12 p25 p28 p31 p33 wait5 endp55 wait1 p53 wait2 endp25 endp28 endp31 endp33 p52 endp53 wait1 p50 wait1 endp52 wait1 endp50 wait1 p25 p28 p31 p33 p52 wait5 endp52 wait3 endp25 endp28 endp31 endp33 wait4 p25 p28 p31 p33 wait8 endp25 endp28 endp31 endp33 wait1 p45 wait2 endp45 wait1 p53 wait12 p26 p29 p33 wait5 endp53 wait1 p52 wait2 endp26 endp29 endp33 p50 endp52 wait1 p49 wait1 endp50 wait1 endp49 wait1 p26 p29 p33 p50 wait5 endp50 wait3 endp26 endp29 endp33 wait4 p26 p29 p33 wait8 endp26 endp29 endp33 wait1 p45 wait2 endp45 wait1 p55 wait12 p28 p31 p37 wait5 endp55 wait1 p53 wait2 endp28 endp31 endp37 p52 endp53 wait1 p50 wait1 endp52 wait1 endp50 wait1 p28 p31 p37 p52 wait5 endp52 wait3 endp28 endp31 endp37 wait4 p28 p31 p37 wait6 p45 wait2 endp28 endp31 endp37 p50 wait1 p53 wait3 p57 wait12 p29 p33 p38 wait11 endp29 endp33 endp38 endp45 endp50 endp53 endp57 wait1 p55 wait5 endp55 wait1 p53 wait5 endp53 wait1 p31 p34 p40 p52 wait5 endp52 wait1 p50 wait5 endp31 endp34 endp40 endp50 wait1'
    piece = read_piece_from_string(s)
    print(piece.to_chord_string(12))


def test_interformat():
    piece = read_piece_from_file('be_son1a.txt')
    sub = piece.sub_piece(0, 512)
    str_clara = sub.to_clara_string()
    f_handle = open('be_son1a.txt', 'r')
    str_target = f_handle.read()
    f_handle.close()
    print(str_clara)
    #str_clara = str_clara + ' '
    #print(str_clara == str_target)

    #print(piece.length / 12)

#test_interformat()
test2()
#main()
#dir_converter('dir1', 'dir1copy', 12 * 4 * 4, 12)