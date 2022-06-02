#!/usr/bin/python3
#
# unilaiva-copy-audio.py3
#
# Part of Unilaiva songbook system.
#
# Copies the .MIDI files created by Lilypond to another location and creates
# mp3 audio from those files in the new location also.
#
# Run with '--help' argument for usage info.
#


import sys
import os
import subprocess
import shutil
import pathlib
import re
import unicodedata


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
    text = text.decode("utf-8")

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
      print ("ERROR (copy midi file skipped): source .midi file is not available")
      return None
    shutil.copy2(self.originalmidifile, destdir.joinpath(self.newmidifilename))
    print(destdir.name + " : " + self.newmidifilename)

  def createaudiofile(self, destdir):
    """
    Creates an mp3 audio file from the MIDI file associated with this song to
    another directory using external software (fluidsynth and ffmpeg). If the
    external software is not available, the file is not created but the script
    continues. The destination directory must exist and be writable. If the
    destination file exists, it will be overwritten.
    """
    if not self.originalmidifile.is_file():
      print("ERROR (create mp3 skipped): source .midi file is not available")
      return None
    if shutil.which("fluidsynth") == None:
      print("ERROR (create mp3 skipped): no fluidsynth executable found")
      return None
    if shutil.which("ffmpeg") == None:
      print("ERROR (create mp3 skipped): no ffmpeg executable found")
      return None
    soundfontfile = pathlib.Path("/usr/share/sounds/sf2/FluidR3_GM.sf2")
    if not soundfontfile.is_file():
      print("ERROR (create mp3 skipped): Soundfont file %s not found"%(soundfontfile))
    cmdoutput = subprocess.run(
      "fluidsynth -a file -T raw -O s16 -E little -r 48000 -F - \"%s\" \"%s\"\
      | ffmpeg -f s32le -ac 1 -ar 48000 -i -\
      -codec:a libmp3lame -f mp3 -q:a 1\
      -id3v2_version 3 -write_id3v2 -write_id3v1 1\
      -metadata title=\"%s [generated from notation]\"\
      -metadata artist=\"Unilaiva audio generator\"\
      -metadata album_artist=\"Unilaiva audio generator\"\
      -metadata track=%d\
      -metadata album=\"%s\"\
      -y \"%s\""
        %(soundfontfile, self.originalmidifile,
          self.title,
          self.nr,
          self.chaptertitle + ' [generated from notation]',
          destdir.joinpath(self.newmp3filename)),
        capture_output=False, shell=True, check=True)

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
          print(countername)
          songnr = int(pretext.split('{',2)[2].split('}',1)[0].strip())
          print(songnr)
      if 'lilypondbook' not in rawsong:
        continue
      songtitle = rawsong.split('\\beginsong',1)[1].split('{',1)[1].split('}',1)[0].strip()
      inputarg = rawsong.split('lilypondbook',1)[1].split('\\input{',1)[1].split('}',1)[0].strip()
      subdir = inputarg.split('/',1)[0]
      midifilename = inputarg.split('-systems.tex',1)[0] + '.midi'
      midifile = basedir.joinpath(midifilename)
      if midifile.is_file(): # add song only if there is a midi file for it
        self.songs.append(Song(self.title, songtitle, songnr, midifile))
      songnr += 1

  def copymidifiles(self, destdir, createsubdir, createaudiofiles):
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

    fullsubdir = destdir
    if createsubdir and len(self.songs) > 0:
      fullsubdir = destdir.joinpath(self.title)
      os.makedirs(fullsubdir, 0o777, True)
    for song in self.songs:
      song.copymidifile(fullsubdir)
      if createaudiofiles:
        song.createaudiofile(fullsubdir)


def execute(depfile, destdir):
  """
  Executes everything: parses the files listed in a .dep file created by
  Lilypond for song chapters and copies the found MIDI files to the
  destination directory.

  Parameters
  ----------
  depfile : pathlib.Path
    The .dep file created by Lilypond
  destdir : pathlib.Path
    The destination directory to copy MIDI files into. The directory must exist.
  """

  # TODO: Get chapter titles from the main .tex file

  basedir = depfile.parent
  with open(depfile, 'r') as depfile:
    deplines = depfile.read().strip().split(' ')

  chapters = []

  for line in deplines:
    if line.startswith('content/songs_'):
      title = line.split('content/songs_',1)[1].split('.tex',1)[0]
      chapters.append(Chapter(title, basedir, basedir.joinpath(line)))

  for chapter in chapters:
    chapter.copymidifiles(destdir, True, True)

# If there is wrong number of arguments or help is requested, print
# usage information and exit with an error code 1.
if len(sys.argv) != 3 or '--help' in sys.argv or '-h' in sys.argv:
  print('unilaiva-copy-audio.py3')
  print('=======================')
  print('')
  print('Copies .midi files created by Lilypond elsewhere.')
  print('')
  print('USAGE:')
  print('')
  print('  copymidifiles <dep-file> <dest-dir>')
  print('')
  print('  <dep-file> is a .dep file created by lilypond')
  print('')
  print('  <dest-dir> destination directory under where the midi files will be')
  print('             copied as a set of subdirectories named after chapters.')
  print('')
  exit(1)

depfile = pathlib.Path(sys.argv[1])
destdir = pathlib.Path(sys.argv[2])

# Check the validity of command line arguments and exit with an error code if
# there is a problem.
if not depfile.is_file():
  print ('Error: ' + depfile.__str__() + ' does not exist')
  exit(2)
if not destdir.is_dir():
  print ('Error: destination directory does not exist')
  exit(2)

# Do what we came here for!
execute(depfile, destdir)
