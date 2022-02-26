import os
from mido import MidiFile
from collections import namedtuple


MAGIC_TOKEN = 'while 0x6969:'


_Event = namedtuple('_Event', 'time note velocity')


def __as_freq(note: int) -> int:
    return round(440.0 * 2 ** ((note - 69) / 12))


def __read_midi(__fp):
    '''Reads a midi file into a list of note-on and note-off events'''
    __midi = MidiFile(__fp)
    __cur_time = 0  # elapsed time in milliseconds
    __ticks_per_beat = __midi.ticks_per_beat

    __events = []

    for __track in __midi.tracks:
        __cur_time = 0
        __cur_tempo = 500  # default: 500 ms/beat
        for __msg in __track:
            __cur_time += __msg.time * __cur_tempo / __ticks_per_beat
            if __msg.type == 'note_on':
                __events.append(
                    _Event(round(__cur_time), __as_freq(__msg.note), __msg.velocity))
            elif __msg.type == 'set_tempo':
                __cur_tempo = __msg.tempo
            elif __msg.type not in {
                'time_signature',
                'control_change',
                'program_change',
                'end_of_track',
                    'track_name'}:
                raise ValueError(
                    f'{__fp} contains unhandled message type: {__msg.type}')

    return sorted(__events)


__header = '''
import time as __time
if 'monotonic_ns' in dir(__time):
    __timer = __time.monotonic_ns
    __scaler = 1000000
else:
    __timer = __time.monotonic
    __scaler = 1e-3
    print('Warning: monotonic_ns not found, using monotonic instead.')
    print('Note this may cause inaccurate timing after 1.165 hour.')

class _Piano:
    def __init__(self):
        self.__loop = False

    def __import_notes(self, __notes):
        self.__notes = __notes
    
    def __import_gpios(self, *__gpios):
        assert len(__gpios), 'No GPIOs specified.'
        if type(__gpios[0]) is list:
            self.__gpios = __gpios[0]
        else:
            self.__gpios = __gpios
        self.__gpio_states = [None] * len(self.__gpios)

    def __reset(self):
        assert __notes in dir(self), 'No notes specified.'
        assert __gpios in dir(self), 'GPIOs not imported.'
        self.__start_time = __timer()
        self.__position = 0

    def __play(self):
        assert __start_time in dir(self), 'Reset the piano'
        assert __position in dir(self), 'Reset the piano'
        
        if len(self.__notes) == self.__position and self.__loop:
            self.__position = 0
            self.__start_time = __timer()
        
        __elapsed = (__timer() - self.__start_time) / __scaler
        __position = self.__position
        for __time, __note, __vel in self.__notes[__position:]:
            if __elapsed < __time:
                return
            self.__position += 1
            
            if __vel: # play note
                for __i, __gpio in enumerate(self.__gpios):
                    if self.__gpio_states[__i]:
                        continue
                    self.__gpio_states[__i] = __note
                    __gpio.frequency = __note
                    __gpio.duty_cycle = __power(__vel)
                    break

            else: # stop note
                for __i, __gpio in enumerate(self.__gpios):
                    if self.__gpio_states[__i] == __note:
                        __gpio.duty_cycpe = 0
                        self.__gpio_states[__i] = None

__piano = _Piano()

def __import_gpios(*__gpios):
    __piano.__import_gpios(__gpios)
'''

__power = '''
def __power(__vel):
    return 0x1000
'''

__play_note_code = '; __piano.__play()'


def __inject(__fp, __notes, __freq=1):
    '''Injects the playing of the notes into a python files for raspberry pi 
    pico's `code.py` file.

    Parameters
    ----------
    __fp : str
        The path to the python file to inject the notes into.
    __notes : list
        The notes to play.
    __freq : int
        The frequency of checking for if a note should be played.
        Defaults to 1.
    '''
    if not __fp.endswith('.py'):
        raise ValueError('File must be a .py file.')
    with open(__fp, 'r') as __f:
        __content = __f.read()

    __content = __content.split(MAGIC_TOKEN)
    if len(__content) != 2:
        raise ValueError('File does not contain magic token.')

    if '__import_gpios' not in __content[0]:
        raise ValueError(
            'You must call `__import_gpios to import your devices.')

    __notes_str = '\n__piano.__import_notes(["' + ','.join([
        f'({__time}, {__note}, {__vel})' for __time, __note, __vel in __notes
        ]) + '"])'

    with open(__fp[:-len('.py')] + '_injected.py', 'w') as __f:
        if '__power' not in __content:
            __f.write(__power)
        __f.write(__header)
        __f.write(__content[0])
        __f.write(__notes_str)
        __f.write('\n__piano.__reset()\n')
        __f.write(MAGIC_TOKEN)

        __line_no = 0
        for __line in __content[1].splitlines():

            __clean_line = __line.replace(' ', '').replace('\t', '')
            if __clean_line:
                __f.write(__line)
                if not __clean_line.startswith('#') and not __line.endswith(':'):
                    __line_no += 1
                    if __line_no % __freq == 0:
                        __f.write(__play_note_code)

            __f.write('\n')


if __name__ == '__main__':
    notes = __read_midi('example.midi')
    __inject('example.py', notes)
