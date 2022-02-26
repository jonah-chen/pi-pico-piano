import os
from mido import MidiFile
from collections import namedtuple


_Event = namedtuple('_Event', 'time note velocity')


def __read_midi(__fp):
    __midi = MidiFile(__fp)
    __cur_time = 0  # elapsed time in milliseconds
    __ticks_per_beat = __midi.ticks_per_beat

    __events = []

    for __track in __midi.tracks:
        __cur_time = 0
        __cur_tempo = 500 # default: 500 ms/beat
        for __msg in __track:
            __cur_time += __msg.time * __cur_tempo / __ticks_per_beat
            if __msg.type == 'note_on':
                __events.append(_Event(__cur_time, __msg.note, __msg.velocity))
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


def __as_freq(note: int) -> int:
    return round(440.0 * 2 ** ((note - 69) / 12))



