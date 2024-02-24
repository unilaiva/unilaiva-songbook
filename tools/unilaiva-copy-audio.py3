#!/usr/bin/python3
#
# unilaiva-copy-audio.py3
#
# Part of Unilaiva songbook system.
#
# Copies the .MIDI files created by Lilypond to another location and creates
# audio files (mp3) from those files in the new location also.
#
# For audio creation, executables 'ffmpeg' and 'fluidsynth', and a sound font
# file are required.
#
# Run with '-h' argument for usage info.
#


import argparse
from argparse import RawDescriptionHelpFormatter
import sys
import os
import subprocess
import shutil
import pathlib
import re
import unicodedata

defaultsffile = '/usr/share/sounds/sf2/FluidR3_GM.sf2'


def strip_accents(text):
    """
    Strip accents from input string.

    Parameters
    ----------
      text : str
        The input string.

    Returns
    -------
    str
      The processed string.
    """
    try:
        text = unicode(text, 'utf-8')
    except (TypeError, NameError): # unicode is a default on Python 3
        pass
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode('utf-8')

    return str(text)

def cleanstr(text):
    """
    Returns the string given as parameter converted to clean ASCII string
    containing only numbers, A-Z, a-z, - and _. Accented characters will
    be returned without their accents and spaces converted to underscores.
    Other unallowed characters will be dropped.

    Parameters
    ----------
    text : str
      The input string.

    Returns
    -------
    str
      The processed string.
    """
    text = strip_accents(text)
    text = re.sub('[ ]+', '_', text)
    text = re.sub('[^0-9a-zA-Z_-]', '', text)

    return text


class Song:
  """Represents one song with a MIDI file associated to it"""
  def __init__(self, chaptertitle, title, nr, midifile):
    """
    Parameters
    ----------
    chapter title : str
      Title of the chapter this song belongs to
    title : str
      Title of the song.
    nr : int
      The number of the song in it's chapter
    midifile : pathlib.Path
      The MIDI file for the song
    """

    self.title = title.split('\\\\',1)[0].strip()
    self.nr = nr
    self.nrstr = str(nr)
    self.originalmidifile = midifile
    self.chaptertitle = chaptertitle
    while len(self.nrstr) < 3:
      self.nrstr = '0' + self.nrstr
    self.newmidifilename = self.nrstr + '_-_' + cleanstr(self.title) + '.midi'
    self.newmp3filename = self.nrstr + '_-_' + cleanstr(self.title) + '_midi' + '.mp3'

  def copymidifile(self, destdir):
    """
    Copies the MIDI file associated with this song to another directory. The
    directory must exist and be writable. If the destination file exists, it
    will be overwritten.

    Parameters
    ----------
    destdir : pathlib.Path
      The destination directory to copy the MIDI file into
    """

    if not self.originalmidifile.is_file():
      print ('ERROR    : source MIDI file is not available')
      exit(4)
    shutil.copy2(self.originalmidifile, destdir.joinpath(self.newmidifilename))
    print(destdir.name + ' : ' + self.newmidifilename)

  def createaudiofile(self, destdir):
    """
    Creates an mp3 audio file from the MIDI file associated with this song to
    another directory using external software (fluidsynth and ffmpeg). The
    destination directory must exist and be writable. If the destination file
    exists, it will be overwritten. The sound font file is picked from global
    variable args.

    Parameters
    ----------
    destdir : pathlib.Path
      The destination directory to create the mp3 file into
    """

    if not self.originalmidifile.is_file():
      print('ERROR    : source MIDI file is not available')
      exit(4)

    try:
      "Check options with: fluidsynth -o help"
      mp3process = subprocess.run(
        'fluidsynth -a file -T raw -O s16 -E little -r 48000 \
        -g 2 -o synth.reverb.level=.9 -o synth.reverb.room-size=0.3 -o synth.reverb.width=1 \
        -F - \"%s\" \"%s\"\
        | ffmpeg -f s32le -ac 1 -ar 48000 -i -\
        -codec:a libmp3lame -f mp3 -q:a 1\
        -id3v2_version 3 -write_id3v2 -write_id3v1\
        -metadata title=\"%s\"\
        -metadata artist=\"Unilaiva audio generator\"\
        -metadata album_artist=\"Unilaiva audio generator\"\
        -metadata track=%d\
        -metadata album=\"%s\"\
        -y \"%s\"'
          %(args.sf, self.originalmidifile,
            self.title + ' [generated from notation]',
            self.nr,
            self.chaptertitle + ' [generated from notation]',
            destdir.joinpath(self.newmp3filename)),
          capture_output=True, shell=True, check=True)
    except subprocess.CalledProcessError as e:
      print('ERROR    : mp3 coversion fails with error %i'%e.returncode)
      print('\n' + e.stderr.decode('utf-8'))
      exit(5)
    print(destdir.name + ' : ' + self.newmp3filename)


class Chapter:
  """Represents a song chapter, a collection of songs"""
  def __init__(self, title, basedir, chapterfile):
    """
    Parameters
    ----------
    title : str
      The title of the chapter
    basedir : pathlib.Path
      Base (root) directory under which midi files can be found; the directory
      where the .dep file resides
    chapterfile : pathlib.Path
      The file containing the songs in this chapter (between beginsong and
      endsong tags)
    """

    self.title = title
    self.cleantitle = cleanstr(self.title)
    self.chapterfile = chapterfile
    self.songs = []

    with open(chapterfile, 'r') as file:
      rawsongs = file.read().split('\endsong')

    songnr = 1
    for rawsong in rawsongs:
      pretext = rawsong.split('\\beginsong',1)[0]
      while '\\setcounter' in pretext:
        pretext = pretext.split('\\setcounter',1)[1]
        countername = pretext.split('{',1)[1].split('}',1)[0].strip()
        if countername == 'songnum':
          #print(countername)
          songnr = int(pretext.split('{',2)[2].split('}',1)[0].strip())
          #print(songnr)
      if 'lilypondbook' not in rawsong:
        songnr += 1
        continue
      songtitle = rawsong.split('\\beginsong',1)[1].split('{',1)[1].split('}',1)[0].strip()
      inputarg = rawsong.split('lilypondbook',1)[1].split('\\input{',1)[1].split('}',1)[0].strip()
      subdir = inputarg.split('/',1)[0]
      midifilename = inputarg.split('-systems.tex',1)[0] + '.midi'
      midifile = basedir.joinpath(midifilename)
      if midifile.is_file(): # add song only if there is a midi file for it
        self.songs.append(Song(self.title, songtitle, songnr, midifile))
      songnr += 1

  def copymidifiles(self, destdir, createsubdir):
    """
    Copies the midi files associated to this chapter to a new directory,
    optionally inside a subdirectory named after the title of this chapter.

    Parameters
    ----------
    destdir : pathlib.Path
      Destination directory. It must exist.
    createsubdir : boolean
      If true, a subdirectory will be created for this chapter's songs under
      the destination directory. The subdir is named after the title of this
      chapter.
    """

    if len(self.songs) == 0:
      return None
    fullsubdir = destdir
    if createsubdir and len(self.songs) > 0:
      fullsubdir = destdir.joinpath(self.title)
      os.makedirs(fullsubdir, 0o777, True)
    for song in self.songs:
      song.copymidifile(fullsubdir)

  def createaudiofiles(self, destdir, createsubdir):
    """
    Creates audio files based on the midi files associated to this chapter to a
    directory, optionally inside a subdirectory named after the title of
    this chapter.

    Parameters
    ----------
    destdir : pathlib.Path
      Destination directory. It must exist.
    createsubdir : boolean
      If true, a subdirectory will be created for this chapter's songs under
      the destination directory. The subdir is named after the title of this
      chapter.
    """

    if len(self.songs) == 0:
      return None
    fullsubdir = destdir
    if createsubdir:
      fullsubdir = destdir.joinpath(self.title)
      os.makedirs(fullsubdir, 0o777, True)
    for song in self.songs:
      song.createaudiofile(fullsubdir)


def execute():
  """
  Executes everything: creates chapters and initiates midi file copying and/or
  mp3 creation for each of them. Gets arguments from global variable args.
  NOTE: Only songs defined in content/songs_*.tex files are included, and each
        such a file is considered a chapter.
  """

  # TODO: Get chapter titles from the main .tex file

  basedir = args.depfile.parent
  with open(args.depfile, 'r') as depfile:
    deplines = depfile.read().strip().split(' ')

  chapters = []

  for line in deplines:
    if line.startswith('content/songs_'):
      title = line.split('content/songs_',1)[1].split('.tex',1)[0]
      chapters.append(Chapter(title, basedir, basedir.joinpath(line)))

  for chapter in chapters:
    if args.midi:
      chapter.copymidifiles(args.destdir, True)
    if args.audio:
      chapter.createaudiofiles(args.destdir, True)


# Main program start

# Parse arguments and check for their validity.

parser = argparse.ArgumentParser(
  description='This utility is part of Unilaiva songbook system.\n\n' +
              'Copies the MIDI files created by lilypond-book to another location, \n' +
              'and creates MP3 audio from those files in the new location also.\n' +
              'Note that only songs defined in content/songs_*.tex files are included,\n' +
              'and each such a file is considered a chapter by which a subdirectory\n' +
              'is created for the songs contained within.',
  formatter_class=RawDescriptionHelpFormatter)
parser.add_argument('depfile', type=pathlib.Path,
                    help='The .dep file created by lilypond-book')
parser.add_argument('destdir', type=pathlib.Path, help='Destination directory under \
                    where the midi and audio files will be copied as a set of \
                    subdirectories named after chapters. The directory must exist.')
parser.add_argument('--sf', type=pathlib.Path, default=defaultsffile,
                    help='Path to a soundfont file. If this argument is not present, \
                    the default %s is used'%defaultsffile)
parser.add_argument('--midi', action='store_true', help='Copy MIDI files')
parser.add_argument('--audio', action='store_true', help='Create MP3 files')

args = parser.parse_args()

if not args.depfile.is_file():
  print('ERROR    : ' + args.depfile.__str__() + ' does not exist')
  exit(2)
if not args.destdir.is_dir():
  print('ERROR    : destination directory does not exist')
  exit(2)
if not args.midi and not args.audio:
  print('ERROR    : No --midi nor --audio argument present: nothing to do!')
  print('           At least one of them is needed.')
  exit(2)
if args.audio:
  if shutil.which('fluidsynth') == None:
    print("ERROR    : 'fluidsynth' executable not found in path!")
    print('           It is required for audio (MP3) creation. Either install it or')
    print('           skip audio creation using by not specifying --audio argument.')
    exit(3)
  if shutil.which('ffmpeg') == None:
    print("ERROR    : 'ffmpeg' executable not found in path!")
    print('           It is required for audio (MP3) creation. Either install it or')
    print('           skip audio creation using by not specifying --audio argument.')
    exit(3)
  if not args.sf.is_file():
    print('ERROR    : Soundfont file not found: %s'%(args.sf))
    print('           It is required for audio (MP3) creation. Either install it, or')
    print('           specify another soundfont file (location) using --sf argument, or')
    print('           skip audio creation using by not specifying --audio argument.')
    exit(3)


# Do what we came here for!
execute()
