#!/usr/bin/python3
#
# unilaiva-generate-json.py3
#
# Part of Unilaiva songbook system.
#
# Generates a JSON file containing information about a song book from
# a songbook's main .tex file. Depends only on standard python libraries.
#
# Run with '-h' argument for usage info.
#
# Author: Lari Natri
#
# License: GPLv3
#

import json
import re
import os
import argparse
from datetime import datetime

class SongbookGenerator:
    """
    Generates a JSON representation of a songbook from a main LaTeX file.

    This class recursively parses LaTeX files, extracts song information,
    chapter titles, and audio links, and organizes them into a structured
    dictionary suitable for JSON output.
    """
    def __init__(self, project_root):
        """
        Initializes the SongbookGenerator.

        Args:
            project_root (str): The absolute path to the project's root directory.
                                This is used to resolve paths for included LaTeX files.
        """
        self.project_root = project_root
        self.visited_paths = set()
        self.song_counter = 1
        self.chapters = [self._new_chapter()]

    def _new_chapter(self, name=""):
        """
        Creates a new chapter dictionary structure.

        Args:
            name (str, optional): The title of the new chapter. Defaults to "".

        Returns:
            dict: A dictionary representing a new chapter.
        """
        return {"chapter_title": name, "chapter_audio_links": [], "songs": []}

    def _clean_latex_macros(self, text):
        """
        Cleans LaTeX macros and special characters from a given text string.

        Args:
            text (str): The input string containing LaTeX macros.

        Returns:
            str: The cleaned string with LaTeX macros replaced or removed.
        """
        # Replace \shrp{} with sharp symbol (♯)
        text = re.sub(r'\\shrp\{\}', '♯', text)
        # Replace \flt{} with flat symbol (♭)
        text = re.sub(r'\\flt\{\}', '♭', text)
        # Remove any other LaTeX macros (e.g., \macro or \macro{arg})
        text = re.sub(r'\\([a-zA-Z]+)(?:\{.*?\})?', '', text)
        # Replace triple dash (---) with em dash (—)
        text = text.replace('---', '—')
        # Replace double dash (--) with en dash (–)
        text = text.replace('--', '–')
        # Replace escaped ampersand (\&) with unescaped ampersand (&)
        text = text.replace(r'\&', '&')
        return text

    def _parse_audio_links(self, content):
        """
        Parses audio links from a given content string.

        Looks for \\audio[key=value]{url} LaTeX commands and extracts
        the URL and any optional key-value pairs.

        Args:
            content (str): The input string to parse for audio links.

        Returns:
            list: A list of dictionaries, where each dictionary represents an
                  audio link with its 'url' and any extracted optional arguments.
        """
        audio_links = []
        audio_matches = re.findall(r'\\audio(\[.*?\])?\{(.*?)\}', content)
        if audio_matches:
            for optional_args_str, url in audio_matches:
                link_data = {}
                url = url.replace('\\%', '%').strip()
                link_data['url'] = url

                if optional_args_str:
                    optional_args = optional_args_str[1:-1]
                    kv_pairs = re.findall(r'([a-zA-Z0-9_\-]+)\s*=\s*([^,]*)(?:,|$)', optional_args)
                    for key, value_raw in kv_pairs:
                        value = value_raw.strip()
                        if value.startswith('{') and value.endswith('}'):
                            value = value[1:-1].strip()
                        link_data[key.strip()] = self._clean_latex_macros(value)
                audio_links.append(link_data)
        return audio_links

    def _parse_one_song(self, song_chunk):
        """
        Parses a single song chunk to extract its title, alternative titles,
        and audio links.

        Args:
            song_chunk (str): A string containing the LaTeX code for a single song,
                              typically starting with \\beginsong.

        Returns:
            dict or None: A dictionary containing the parsed song data if successful,
                          otherwise None. The dictionary includes:
                          - 'number': The sequential song number.
                          - 'title': The main title of the song.
                          - 'alt_titles' (optional): A list of alternative titles.
                          - Other key-value pairs extracted from optional arguments.
                          - 'audio_links': A list of dictionaries for audio links.
        """
        song_data = {}
        # Match the title in curly braces and then an optional part in square brackets
        # The second group (optional_args_str) will be None if no optional args are present
        header_match = re.search(r'^\s*\{(.*?)\}\s*(\[.*?\])?', song_chunk, re.DOTALL)
        if not header_match:
            return None

        song_data['number'] = self.song_counter
        full_title_string = header_match.group(1).strip()
        # Split by '\\' to handle multiple titles separated by this LaTeX command
        title_parts = [self._clean_latex_macros(p.strip()) for p in full_title_string.split(r'\\')]
        song_data['title'] = title_parts[0]
        if len(title_parts) > 1:
            if 'alt_titles' not in song_data:
                song_data['alt_titles'] = []
            song_data['alt_titles'].extend(title_parts[1:])

        optional_args_str = header_match.group(2)
        if optional_args_str:
            # Remove the leading and trailing square brackets
            optional_args_str = optional_args_str[1:-1]
            # Find all key=value pairs. Values can be in curly braces or not.
            # This regex is more robust for various formats like key=value, key={value}, key=value,key2=value2
            kv_pairs = re.findall(r'([a-zA-Z0-9_\\-]+)\s*=\s*(?:\{(.*?)\}|(.*?))(?:,|$)', optional_args_str)
            alt_titles = []
            for key, val1, val2 in kv_pairs:
                value = val1 if val1 is not None else val2
                if value is not None:
                    cleaned_value = self._clean_latex_macros(value.strip())
                    if key.strip() == 'ititle':
                        alt_titles.append(cleaned_value)
                    else:
                        song_data[key.strip()] = cleaned_value
            if alt_titles:
                song_data['alt_titles'] = alt_titles

        song_data['audio_links'] = self._parse_audio_links(song_chunk)

        self.song_counter += 1
        return song_data

    def collect_songs_recursively(self, filepath):
        """
        Recursively collects songs, chapters, and audio links from LaTeX files.

        This method parses the given LaTeX file, identifies song definitions,
        chapter declarations (\\mainchapter), song number resets (\\setcounter{songnum}),
        and included files (\\input, \\include). It then recursively calls itself
        for included files to build a complete songbook structure.

        Args:
            filepath (str): The absolute path to the LaTeX file to process.
        """
        filepath = os.path.abspath(filepath)
        if filepath in self.visited_paths:
            return

        if not os.path.exists(filepath):
            if os.path.exists(filepath + '.tex'):
                filepath = filepath + '.tex'
            else:
                print(f"Warning: Could not find file {filepath}")
                return

        self.visited_paths.add(filepath)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: could not read file {filepath}: {e}")
            return

        current_dir = os.path.dirname(filepath)
        
        # Split the content by LaTeX commands that indicate structural changes
        # such as new chapters, song number resets, or file inclusions.
        parts = re.split(r'(\\mainchapter{.*?}|\\setcounter{songnum}{.*?}|\\input{.*?}|\\include{.*?})', content)

        for part in parts:
            if not part:
                continue

            stripped_part = part.strip()
            mainchapter_match = re.match(r'\\mainchapter{(.*?)}', stripped_part)
            setcounter_match = re.match(r'\\setcounter{songnum}{(.*?)}', stripped_part)
            include_match = re.match(r'\\(?:input|include){(.*?)}', stripped_part)

            if mainchapter_match:
                chapter_title = mainchapter_match.group(1).strip()
                last_chap = self.chapters[-1]
                # If the last chapter is empty (no songs or audio links) and has no title,
                # update its title. Otherwise, create a new chapter.
                if not last_chap["songs"] and not last_chap["chapter_audio_links"] and last_chap["chapter_title"] == "":
                    last_chap["chapter_title"] = chapter_title
                else:
                    self.chapters.append(self._new_chapter(chapter_title))
            elif setcounter_match:
                try:
                    new_count = int(setcounter_match.group(1).strip())
                    self.song_counter = new_count
                except ValueError:
                    print(f"Warning: could not parse song number from {stripped_part}")
            elif include_match:
                include_path = include_match.group(1).strip()
                # Try to resolve the include path relative to the current file's directory
                path_from_current = os.path.join(current_dir, include_path)
                
                # Check if the file exists with or without a .tex extension
                if os.path.exists(path_from_current) or (not include_path.endswith('.tex') and os.path.exists(path_from_current + '.tex')):
                    included_file_path = path_from_current
                else:
                    # If not found relative to current, try resolving relative to the project root
                    included_file_path = os.path.join(self.project_root, include_path)
                
                self.collect_songs_recursively(included_file_path)
            else:
                # Process content that is not a chapter, setcounter, or include command.
                # This content might contain song definitions or chapter-level audio links.
                sub_chunks = re.split(r'(\\beginsong)', part)
                
                # The first sub_chunk (before the first \beginsong) might contain chapter-level audio links
                chapter_level_content = sub_chunks[0]
                chapter_audio = self._parse_audio_links(chapter_level_content)
                if chapter_audio:
                    self.chapters[-1]['chapter_audio_links'].extend(chapter_audio)

                # Iterate through the remaining sub_chunks, which should start with \beginsong
                for i in range(1, len(sub_chunks), 2):
                    if i + 1 < len(sub_chunks):
                        song_content = sub_chunks[i+1]
                        song = self._parse_one_song(song_content)
                        if song:
                            self.chapters[-1]['songs'].append(song)

def main():
    """
    Main function to parse command-line arguments, initialize the SongbookGenerator,
    collect song data, and output it as a JSON file.
    """
    parser = argparse.ArgumentParser(
        description='''
Generate a JSON file containing structured information about a songbook.

This script parses a Unilaiva songbook's main LaTeX (.tex) file, recursively
processes included files, and extracts song titles, alternative titles, audio
links, and chapter information. It outputs a JSON file that can be used for
various purposes, such as generating web-based song indexes or other digital
representations of the songbook.

Example usage:
  python3 unilaiva-generate-json.py3 /path/to/your/main_songbook.tex

The output JSON file will be created in the same directory as the
main_songbook.tex file, with a .json extension (e.g., main_songbook.json).
''',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('main_songbook_file', help='The main songbook .tex file.')
    args = parser.parse_args()

    main_songbook_file = os.path.abspath(args.main_songbook_file)
    project_root = os.path.dirname(main_songbook_file)

    generator = SongbookGenerator(project_root)
    generator.collect_songs_recursively(main_songbook_file)

    # Filter out any empty chapters that might have been created
    generator.chapters = [c for c in generator.chapters if c['songs'] or c['chapter_audio_links']]

    # Determine the output filename and path
    output_filename = os.path.splitext(os.path.basename(main_songbook_file))[0] + '.json'
    output_path = os.path.join(os.path.dirname(main_songbook_file), output_filename)
    
    output_data = {
        "songbook_main_file": os.path.basename(main_songbook_file),
        "generated_time": datetime.now().isoformat(),
        "chapters": generator.chapters
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_path}")

if __name__ == '__main__':
    main()
