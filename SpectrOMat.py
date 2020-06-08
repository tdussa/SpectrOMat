#! /usr/bin/env python
# -*- coding: utf-8 -*-

###
# Grab OceanOptics spectrometer output and visualize it.
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

try:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter
    input = raw_input
except ImportError:
    # for Python3
    from tkinter import *   ## notice here too
from math import log
import numpy
import time

# Plotting
import matplotlib.animation as animation
import matplotlib.pyplot as plot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
SpectrOMat_animation = None

# Audio
import pygame

# SeaBreeze USB spectrometer access library
try:
    import seabreeze
    seabreeze.use("pyseabreeze")
    import seabreeze.spectrometers as sb
except ImportError:
    # Library not installed
    sb = None


# Global helper function
def StringIsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# SeaBreeze spectrograph simulator
class SBSimulator:
    """SeaBreeze specrograph simulator class"""
    def __init__(self,
                 integration_time_micros=100000,
                 minimum_integration_time_micros = 8000,
                 wavelengths=list(range(2048)),
                 generator=numpy.random.normal,
                 histogram=True):
        self._integration_time_micros = integration_time_micros
        self.minimum_integration_time_micros = minimum_integration_time_micros
        self._wavelengths = wavelengths
        self.samplesize = len(wavelengths)
        self.generator = generator
        self.histogram = histogram

    def integration_time_micros(self, newValue):
        if (newValue >= self.minimum_integration_time_micros):
            self._integration_time_micros = newValue

    def intensities(self):
        time.sleep(self._integration_time_micros / 1000000)
        if self.histogram:
            return(numpy.histogram(self.generator(size=self.samplesize), bins=self.samplesize)[0])
        else:
            return(self.generator(size=self.samplesize))

    def wavelengths(self):
        return(self._wavelengths)



class SpectrOMat:
    """Real-time spectrum analyzer class"""

    def __init__(self,
                 autoexposure=False,
                 autorepeat=False,
                 autosave=True,
                 dark_frames=1,
                 device='#0',
                 enable_audio=True,
                 enable_plot=True,
                 output_file='Snapshot-%Y-%m-%dT%H:%M:%S%z.dat',
                 root=None,
                 scan_frames=1,
                 scan_time=100000,
                 timestamp='%Y-%m-%dT%H:%M:%S%z',
                 ):
        """Class initializer"""
        self.init_device(device=device)
        self.init_tk(root=root)
        self.init_variables(
                            autoexposure=autoexposure,
                            autorepeat=autorepeat,
                            autosave=autosave,
                            dark_frames=dark_frames,
                            enable_audio=enable_audio,
                            enable_plot=enable_plot,
                            output_file=output_file,
                            scan_frames=scan_frames,
                            scan_time=scan_time,
                            timestamp=timestamp,
                            )
        self.init_plot()
        self.init_audio()
        self.init_ui()
                           

    def init_device(self, device='#0'):
        """Initialize spectrometer device"""
        try:
            if ('SIMULATOR'.startswith(device.upper())):
                self.spectrometer = SBSimulator()
            elif (device[0] == '#'):
                self.spectrometer = sb.Spectrometer(sb.list_devices()[int(device[1:])])
            else:
                self.spectrometer = sb.Spectrometer.from_serial_number(device)
        except:
            print('ERROR: Could not initialize device "' + device + '"!')
            if (sb is None):
                print('SeaBreeze library not found!')
            else:
                print('Available devices:')
                index = 0
                for dev in sb.list_devices():
                    print(' - #' + str(index) + ':', 'Model:', dev.model + '; serial number:', dev.serial)
                    index += 1
            if ('Y'.startswith(input('Simulate spectrometer device instead?  [Y/n] ').upper())):
                self.spectrometer = SBSimulator()
            else:
                sys.exit(1)
        self.wavelengths = self.spectrometer.wavelengths()
        self.samplesize = len(self.wavelengths)


    def init_tk(self, root=None):
        """Initialize TK subsystem"""
        if root is None:
            root = Tk()
        self.root = root
        self.root.title('Spectr-O-Mat')


    def init_variables(self,
                       autoexposure=False,
                       autorepeat=False,
                       autosave=True,
                       dark_frames=1,
                       enable_audio=True,
                       enable_plot=True,
                       output_file='Snapshot-%Y-%m-%dT%H:%M:%S%z.dat',
                       root=None,
                       scan_frames=1,
                       scan_time=100000,
                       timestamp='%Y-%m-%dT%H:%M:%S%z',
                       ):
        """Initialize instance variables"""
        self.run_measurement = False
        self.have_darkness_correction = False
        self.button_startpause_texts = { True: 'Pause Measurement', False: 'Start Measurement' }
        self.button_stopdarkness_texts = { True: 'Stop Measurement', False: 'Get Darkness Correction' }

        self.autoexposure = IntVar(value=autoexposure)
        self.autorepeat = IntVar(value=autorepeat)
        self.autosave = IntVar(value=autosave)
        self.dark_frames = StringVar(value=dark_frames)
        self.enable_audio = IntVar(value=enable_audio)
        self.enable_plot = IntVar(value=enable_plot)
        self.output_file = StringVar(value=output_file)
        self.scan_frames = StringVar(value=scan_frames)
        self.scan_time = StringVar(value=scan_time)
        self.timestamp = timestamp

        self.message = StringVar()

        self.total_exposure = int(scan_frames) * int(scan_time)

        # Initialize measurement variables
        self.darkness_correction = [0.0]*(self.samplesize)
        self.measurement = 0
        self.data = [0.0]*(self.samplesize)


    def init_plot(self):
        """Initialize plotting subsystem"""
        self.figure = plot.figure()
        self.axes = self.figure.gca()
        self.graph, = self.axes.plot(self.wavelengths, self.data)
        self.figure.suptitle('No measurement taken so far.')
        self.axes.set_xlabel('Wavelengths [nm]')
        self.axes.set_ylabel('Intensity [count]')
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)


    def init_audio(self):
        """Initialize sound subsystem"""
        # Set sound vars
        samplerate = 44100  # audio sample rate [Hz]
        amplitude = 32767   # audio amplitude
        fade = 50           # audio fade-in/fade-out time [ms]
        squelch = 50        # noise-suppression factor

        # Initialize stuff
        pygame.mixer.pre_init(44100, -16, 1, 1024)
        pygame.init()

        self.sound = None


    def init_ui(self):
        """Start the UI"""
	# Define the elements
        self.label_scan_frames = Label(self.root, text='Scan Frame Count', justify=LEFT)
        self.scale_scan_frames = Scale(self.root, from_=0, to=10000, showvalue=0, orient=HORIZONTAL, command=self.update_scan_frames)
        self.entry_scan_frames = Entry(self.root, textvariable=self.scan_frames, validate='focusout')

        self.label_scan_time = Label(self.root, text='Scan Time [µs]', justify=LEFT)
        self.scale_scan_time = Scale(self.root, from_=self.spectrometer.minimum_integration_time_micros, to=10000000, showvalue=0, orient=HORIZONTAL, command=self.update_scan_time)
        self.entry_scan_time = Entry(self.root, textvariable=self.scan_time, validate='focusout')

        self.label_dark_frames = Label(self.root, text='Dark Frame Count', justify=LEFT)
        self.scale_dark_frames = Scale(self.root, from_=1, to=10000, showvalue=0, orient=HORIZONTAL, command=self.update_dark_frames)
        self.entry_dark_frames = Entry(self.root, textvariable=self.dark_frames, validate='focusout')

        self.entry_scan_frames.config({'validatecommand': self.validate_scan_frames})
        self.entry_scan_time.config({'validatecommand': self.validate_scan_time})
        self.entry_dark_frames.config({'validatecommand': self.validate_dark_frames})

        self.button_startpause_text = StringVar()
        self.button_startpause_text.set(self.button_startpause_texts[self.run_measurement])
        self.button_startpause = Button(self.root, textvariable=self.button_startpause_text, command=self.startpause)

        self.checkbutton_enable_plot = Checkbutton(self.root, text='Enable Live Plotting', variable=self.enable_plot)
        self.checkbutton_enable_audio = Checkbutton(self.root, text='Enable Live Audio', variable=self.enable_audio)

        self.checkbutton_autorepeat = Checkbutton(self.root, text='Auto Repeat', variable=self.autorepeat)
        self.checkbutton_autosave = Checkbutton(self.root, text='Auto Save', variable=self.autosave)
        self.checkbutton_autoexposure = Checkbutton(self.root, text='Constant Total Exposure', variable=self.autoexposure)

        self.button_stopdarkness_text = StringVar()
        self.button_stopdarkness_text.set(self.button_stopdarkness_texts[self.run_measurement])
        self.button_stopdarkness = Button(self.root, textvariable=self.button_stopdarkness_text, command=self.stopdarkness)

        self.button_save = Button(self.root, text='Save to File', command=self.save)
        self.button_reset = Button(self.root, text='Reset', command=self.reset)
        self.button_exit = Button(self.root, text='Exit', command=self.exit)

        self.textbox = Label(self.root, fg='white', bg='black', textvariable=self.message)
        self.message.set('Ready.')

        # Define the layout
        self.label_scan_frames.grid(rowspan=2)
        self.scale_scan_frames.grid(row=0, column=1, rowspan=2, columnspan=2, sticky='ew')
        self.entry_scan_frames.grid(row=1, column=3)

        self.label_scan_time.grid(rowspan=2)
        self.scale_scan_time.grid(row=2, column=1, rowspan=2, columnspan=2, sticky='ew')
        self.entry_scan_time.grid(row=3, column=3)

        self.label_dark_frames.grid(rowspan=2)
        self.scale_dark_frames.grid(row=4, column=1, rowspan=2, columnspan=2, sticky='ew')
        self.entry_dark_frames.grid(row=5, column=3)

        self.checkbutton_autorepeat.grid(row=6)
        self.checkbutton_autosave.grid(row=6, column=1, columnspan=2)
        self.checkbutton_autoexposure.grid(row=6, column=3)

        self.button_startpause.grid(row=7)
        self.checkbutton_enable_plot.grid(row=7, column=1)
        self.checkbutton_enable_audio.grid(row=7, column=2)
        self.button_stopdarkness.grid(row=7, column=3)

        self.button_save.grid(row=8)
        self.button_reset.grid(row=8, column=1, columnspan=2)
        self.button_exit.grid(row=8, column=3)

        self.textbox.grid(columnspan=4)

        self.canvas.get_tk_widget().grid(columnspan=4)

	# Start the infinite measurement loop
        self.root.after(1, self.measure)


    def update_scan_frames(self, newValue):
        newValue = int(newValue)
        if self.autoexposure.get() > 0:
            if newValue == 0 or newValue * 10000000 > self.total_exposure:
                newValue = int(self.total_exposure / 10000000)
                if newValue == 0:
                    newValue = 1
                self.scale_scan_frames.set(newValue)
            elif newValue * self.spectrometer.minimum_integration_time_micros < self.total_exposure:
                newValue = int(self.total_exposure / self.spectrometer.minimum_integration_time_micros)
                self.scale_scan_frames.set(newValue)
            newTime = int(self.total_exposure / newValue)
            print('v', newValue)
            print('t: ', newTime)
            #self.scan_time.set(newTime)
            self.scale_scan_time.set(newTime)
        self.scan_frames.set(newValue)
        self.dark_frames.set(newValue)
        self.scale_dark_frames.set(newValue)
        self.total_exposure = int(self.scan_frames.get()) * int(self.scan_time.get())


    def validate_scan_frames(self):
        newValue = self.scan_frames.get()
        if StringIsInt(newValue) and \
           int(newValue) >= 0 and \
           int(newValue) <= 10000:
            self.scale_scan_frames.set(int(newValue))
            self.scale_dark_frames.set(int(newValue))
            self.dark_frames.set(newValue)
        else:
            self.scan_frames.set(self.scale_scan_frames.get())
            self.entry_scan_frames.after_idle(self.entry_scan_frames.config, {'validate': 'focusout', 'validatecommand': self.validate_scan_frames})
        return True


    def update_scan_time(self, newValue):
        newValue = int(newValue)
        if self.autoexposure.get() > 0 and \
           int(self.scan_frames.get()) != 0:
            if newValue * 10000 > self.total_exposure:
                newValue = int(self.total_exposure / 10000)
                print(newValue)
                self.scale_scan_time.set(newValue)
            newFrames = int(self.total_exposure / newValue)
            self.scan_frames.set(newFrames)
            self.dark_frames.set(newFrames)
            self.scale_scan_frames.set(newFrames)
            self.scale_dark_frames.set(newFrames)
        self.scan_time.set(newValue)
        self.spectrometer.integration_time_micros(newValue)
        self.total_exposure = int(self.scan_frames.get()) * int(self.scan_time.get())


    def validate_scan_time(self):
        newValue = self.scan_time.get()
        if StringIsInt(newValue) and \
           int(newValue) >= self.spectrometer.minimum_integration_time_micros and \
           int(newValue) <= 10000000:
            self.scale_scan_time.set(int(newValue))
        else:
            self.scan_time.set(self.scale_scan_time.get())
            self.entry_scan_time.after_idle(self.entry_scan_time.config, {'validate': 'focusout', 'validatecommand': self.validate_scan_time})
        return True


    def update_dark_frames(self, newValue):
        self.dark_frames.set(newValue)


    def validate_dark_frames(self):
        newValue = self.dark_frames.get()
        if StringIsInt(newValue) and \
           int(newValue) >= 1 and \
           int(newValue) <= 10000:
            self.scale_dark_frames.set(int(newValue))
        else:
            self.dark_frames.set(self.scale_scan_frames.get())
            self.entry_dark_frames.after_idle(self.entry_dark_frames.config, {'validate': 'focusout', 'validatecommand': self.validate_dark_frames})
        return True


    def startpause(self):
        self.run_measurement = not self.run_measurement
        self.button_startpause_text.set(self.button_startpause_texts[self.run_measurement])
        self.button_stopdarkness_text.set(self.button_stopdarkness_texts[self.run_measurement])


    def stopdarkness(self):
        if self.run_measurement:
            self.run_measurement = False
            self.button_startpause_text.set(self.button_startpause_texts[self.run_measurement])
            self.button_stopdarkness_text.set(self.button_stopdarkness_texts[self.run_measurement])
            self.message.set('Ready.')
            self.measurement = 0
        else:
            newData = self.spectrometer.intensities()
            count = 1
            self.message.set('Scanning dark frame ' + str(count) + '/' + str(self.dark_frames.get()))
            self.root.update()
            while count < int(self.dark_frames.get()):
                newData = list(map(lambda x,y:x+y, self.spectrometer.intensities(), newData))
                if (count % 100 == 0):
                    print('O', end='', flush=True)
                elif (count % 10 == 0):
                    print('o', end='', flush=True)
                else:
                    print('.', end='', flush=True)
                count += 1
                self.message.set('Scanning dark frame ' + str(count) + '/' + str(self.dark_frames.get()))
                self.root.update()
            self.darkness_correction = list(map(lambda x:x/count, newData))
            self.have_darkness_correction = True
            self.axes.set_ylabel('Intensity [corrected count]')
            self.message.set(str(self.dark_frames.get()) + ' dark frames scanned. Ready.')
            print(str(self.dark_frames.get()) + ' dark frames scanned.')


    def save(self):
        try:
            with open(time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()), 'w') as f:
                f.write('# Spectr-O-Mat data format: 2')
                f.write('\n# Time of snapshot: ' + time.strftime(self.timestamp, time.gmtime()))
                f.write('\n# Number of frames accumulated: ' + str(self.measurement))
                f.write('\n# Scan time per exposure [µs]: ' + str(self.scan_time.get()))
                if self.have_darkness_correction:
                    f.write('\n# Number of dark frames accumulated: ' + str(self.dark_frames.get()))
                    f.write('\n# Wavelength [nm], dark frame correction data [averaged count]:\n# ')
                    f.write('\n# '.join(map(lambda x,y:str(x)+', '+str(y), self.spectrometer.wavelengths(), self.darkness_correction)))
                    f.write('\n# Wavelength [nm], Intensity [corrected count]:\n')
                else:
                    f.write('\n# Number of dark frames accumulated: None.')
                    f.write('\n# Wavelength [nm], Intensity [count]:\n')
                f.write('\n'.join(map(lambda x,y:str(x)+', '+str(y), self.spectrometer.wavelengths(), self.data)) + '\n')
            self.message.set('Data saved to ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()) + '. Ready.')
            print('Data saved to ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()))
        except:
            self.message.set('Error while writing ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()) + '. Ready.')
            print('Error while writing ' + time.strftime('Snapshot-%Y-%m-%dT%H:%M:%S.dat', time.gmtime()))
        self.root.update()


    def reset(self):
        self.run_measurement = False
        self.button_startpause_text.set(self.button_startpause_texts[self.run_measurement])
        self.button_stopdarkness_text.set(self.button_stopdarkness_texts[self.run_measurement])
        self.darkness_correction = [0.0]*(len(self.spectrometer.wavelengths()))
        self.have_darkness_correction = False
        self.data = [0.0]*(len(self.spectrometer.wavelengths()))
        self.figure.suptitle('No measurement taken so far.')
        self.axes.set_ylabel('Intensity [count]')
        self.measurement = 0
        self.message.set('All parameters reset. Ready.')


    def exit(self):
        sys.exit(0)


    def update_plot(self, i):
        scan_frames = int(self.scan_frames.get())
        if (self.measurement == scan_frames) or \
           (self.enable_plot.get() > 0):
            self.graph.set_ydata(self.data)
            self.axes.relim()
            self.axes.autoscale_view(True, True, True)
        

    def measure(self):
        if self.run_measurement:
            scan_frames = int(self.scan_frames.get())
            if (scan_frames > 0):
                self.message.set('Scanning frame ' + str(self.measurement+1) + '/' + str(scan_frames) + '...')
            else:
                self.message.set('Scanning frame...')
            self.root.update()
            newData = list(map(lambda x,y:x-y, self.spectrometer.intensities(), self.darkness_correction))
            if (self.measurement == 0):
                self.data = newData
            else:
                self.data = list(map(lambda x,y:x+y, self.data, newData))
            self.measurement += 1

            plot.suptitle(time.strftime(self.timestamp, time.gmtime()) +
                         ' (sum of ' + str(self.measurement) + ' measurement(s)' +
                         ' with scan time ' + str(self.scan_time.get()) + ' µs)')

            if (self.measurement % 100 == 0):
                print('O', end='', flush=True)
            elif (self.measurement % 10 == 0):
                print('o', end='', flush=True)
            else:
                print('.', end='', flush=True)
            if (scan_frames > 0):
                if self.measurement % scan_frames == 0:
                    self.update_plot(0)
                    if self.autosave.get() != 0:
                        self.save()
                    self.measurement = 0
                    if self.autorepeat.get() == 0:
                        self.run_measurement = False
                        self.button_startpause_text.set(self.button_startpause_texts[self.run_measurement])
                        self.button_stopdarkness_text.set(self.button_stopdarkness_texts[self.run_measurement])
                        self.message.set('Ready.')

        self.root.after(1, self.measure)


def main(device='#0', scan_time=100000, scan_frames=1, timestamp='%Y-%m-%dT%H:%M:%S%z'):
    spectromat = SpectrOMat(device=device, scan_time=scan_time, scan_frames=scan_frames, timestamp=timestamp)
    SpectrOMat_animation = animation.FuncAnimation(spectromat.figure, spectromat.update_plot)
    spectromat.root.mainloop()

if __name__ == "__main__":
    # Print license info
    print('''
SpectrOMat Copyright (C) 2017-2020 Tobias Dussa
This program comes with ABSOLUTELY NO WARRANTY; for details see LICENSE.
This is free software, and you are welcome to redistribute it
under certain conditions; refer to LICENSE for details.
    ''');

    # Parse args
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-d', '--device', dest='device', default='#0', help='input device to use; "<serial number>" or "#<device number>" or "SIMULATOR" (default: #0)')
    parser.add_argument('-r', '--scan_frames', dest='scan_frames', default='1', help='reset after n measurement cycles with 0 meaning indefinite (default: 1)')
    parser.add_argument('-s', '--scan_time', dest='scan_time', default='100000', help='scan time in microseconds (default: 100000)')
    parser.add_argument('-t', '--timestamp',  dest='timestamp', default='%Y-%m-%dT%H:%M:%S%z', help='itemstamp format string (default: "%%Y-%%m-%%dT%%H:%%M:%%S%%z")')
    args = parser.parse_args()

    main(args.device, args.scan_time, args.scan_frames, args.timestamp)
