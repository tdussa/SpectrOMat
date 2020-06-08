#! /usr/bin/env python
# -*- coding: utf-8 -*-

###
# Grab SpectrOMat snapshot files and try to play them as audio.
# Copyright (C) 2017-2020 Tobias Dussa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
###

from time import sleep
import sys
import contextlib

import numpy
import pygame

channels = 2048     # number of audio channels
samplerate = 44100  # audio sample rate [Hz]
amplitude = 32767   # audio amplitude
fade = 50           # audio fade-in/fade-out time [ms]


def synthesize_sound(amplitudes):
    spectrum = numpy.concatenate([numpy.zeros(100), amplitudes, numpy.zeros(samplerate - len(amplitudes) - 99)])
    sample = numpy.fft.irfft(spectrum).real
    return(normalize(sample, amplitude).astype(numpy.int16))


def normalize(amplitudes, amplitude=1):
    loudness = numpy.max(numpy.abs(amplitudes), axis=0)
    if (loudness > 0):
        amplitudes = numpy.multiply(amplitudes, amplitude/loudness)
    return(amplitudes)


def fadeout(sound):
    sound.fadeout(fade)
    pygame.time.wait(fade)


def demo():
    demodelay=100
    
    index = numpy.random.normal(size=channels)
    newsound = pygame.sndarray.make_sound(synthesize_sound(index))
    newsound.play(-1, fade_ms=fade)
    oldsound=newsound
    for count in range(8):
        pygame.time.wait(demodelay)
        print(count)
        index = numpy.random.normal(size=channels)
        newsound = pygame.sndarray.make_sound(synthesize_sound(index))
        fadeout(oldsound)
        newsound.play(-1, fade_ms=fade)
        oldsound=newsound

    index = numpy.zeros(channels)
    index[0:1] = numpy.ones(1)
    newsound = pygame.sndarray.make_sound(synthesize_sound(index))
    fadeout(oldsound)
    newsound.play(-1, fade_ms=fade)
    oldsound=newsound
    for count in range(32):
        pygame.time.wait(demodelay)
        print(count)
        index = numpy.roll(index, 177)
        newsound = pygame.sndarray.make_sound(synthesize_sound(index))
        fadeout(oldsound)
        newsound.play(-1, fade_ms=fade)
        oldsound=newsound

    index = numpy.zeros(channels)
    index[0:200] = numpy.ones(200)
    newsound = pygame.sndarray.make_sound(synthesize_sound(index))
    fadeout(oldsound)
    newsound.play(-1, fade_ms=fade)
    oldsound=newsound
    for count in range(32):
        pygame.time.wait(demodelay)
        print(count)
        index = numpy.roll(index, 450)
        newsound = pygame.sndarray.make_sound(synthesize_sound(index))
        fadeout(oldsound)
        newsound.play(-1, fade_ms=fade)
        oldsound=newsound


@contextlib.contextmanager
def _smart_open(filename, mode='Ur'):
    if filename == '-':
        if mode is None or mode == '' or 'r' in mode:
            fh = sys.stdin
        else:
            fh = sys.stdout
    else:
        fh = open(filename, mode)
    try:
        yield fh
    finally:
        if filename is not '-':
            fh.close()

if __name__ == "__main__":
    # Print license info
    print('''
SpectrOMat play_snapshot Copyright (C) 2017-2020 Tobias Dussa
This program comes with ABSOLUTELY NO WARRANTY; for details see LICENSE.
This is free software, and you are welcome to redistribute it
under certain conditions; refer to LICENSE for details.
    ''');

    args = sys.argv[1:]

    pygame.mixer.pre_init(44100, -16, 1, 1024)
    pygame.init()

    if args == []:
        demo()
        sys.exit(0)

    sound = None
    for filearg in args:
        data = []
        print(filearg)
        with _smart_open(filearg) as handle:
            for line in handle:
                if line.startswith('#'):
                    continue 
                data.append(float(line.split()[-1]))
        data = normalize(data, 50)
        data = numpy.exp(data)
        data = normalize(data)
        if not sound is None:
            fadeout(sound)
        sound = pygame.sndarray.make_sound(synthesize_sound(data))
        sound.play(-1, fade_ms=fade)
        pygame.time.wait(2500)
