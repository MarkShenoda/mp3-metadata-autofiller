import os
import sys
from dotenv import load_dotenv
load_dotenv()


from string import ascii_letters, digits, whitespace
from urllib.request import urlopen

import keyboard

import tkinter
from tkinter.filedialog import askopenfilenames

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError, TALB, TPE1, TPE2, TCON, TYER, TRCK, TIT2, APIC, TPOS
from mutagen.flac import FLAC, Picture


class Song:
    def __init__(self, title, artist, path):
        self.title = title
        self.artist = artist
        self.path = path

import os

def main():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")



    file_paths = get_input_files()
    song_list, wrong_file_extension, wrong_name_format = get_tracks_and_artists(file_paths)

    if wrong_file_extension:
        print("One or more files are not MP3 or FLAC. Offending files:\n")
        for file in wrong_file_extension:
            print(file)
        print()
        exit_routine()

    if wrong_name_format:
        print("One or more filenames are not in the format \"Artist Name - Track Name\". Offending files:\n")
        for file in wrong_name_format:
            print(file)
        print()
        exit_routine()

    credentials_manager = SpotifyClientCredentials(client_id, client_secret)
    spotify = spotipy.Spotify(client_credentials_manager=credentials_manager)

    error_list, no_genre_list = obtain_and_edit_metadata(song_list, spotify)

    #print("\nScript complete!\n", spotify)

    if error_list:
        print("Spotify could not find metadata for the following tracks:\n")
        for song in error_list:
            print(f"{song.artist} - {song.title}")
        print()

    if no_genre_list:
        print("Spotify could not find genre data for the following tracks:\n")
        for song in no_genre_list:
            print(f"{song.artist} - {song.title}")
        print()

    print("Thank you for using the Metadata Autofiller.\n")
    exit_routine()


def obtain_and_edit_metadata(song_list, spotify):
    error_list = []
    no_genre_list = []

    for song in song_list:
        if set(song.title).difference(ascii_letters + digits + whitespace):
            print(f"\n{song.artist} - {song.title} has special characters. Searching by title only.")
            track_query = spotify.search(q=song.title, limit=1)
        else:
            track_query = spotify.search(q=f"artist:{song.artist} track:{song.title}", limit=1)
            #print("track query",track_query)

        try:
            item = track_query['tracks']['items'][0]
            song_name = item['name']
            album_name = item['album']['name']
            release_year = item['album']['release_date'][:4]
            track_number = str(item['track_number'])
            total_tracks = str(item['album']['total_tracks'])
            disk_number = str(item['disc_number'])
            album_artist = item['album']['artists'][0]['name']
            album_art = item['album']['images'][0]['url']
        except IndexError:
            print(f"Failed to add metadata to {song.artist} - {song.title}!")
            error_list.append(song)
            continue

        song_artists = [artist['name'] for artist in item['artists']]
        genre_query = spotify.search(q=f"artist:{album_artist}", type="artist", limit=1)
        genres = genre_query['artists']['items'][0].get('genres', [])

        if not genres:
            no_genre_list.append(song)

        try:
            if song.path.endswith(".mp3"):
                try:
                    audio_file = MP3(song.path)
                except ID3NoHeaderError:
                    audio_file = mutagen.File(song.path, easy=True)
                    audio_file.add_tags()

                audio_file['TIT2'] = TIT2(encoding=3, text=song_name)
                audio_file['TPE1'] = TPE1(encoding=3, text=", ".join(song_artists))
                audio_file['TALB'] = TALB(encoding=3, text=album_name)
                audio_file['TPE2'] = TPE2(encoding=3, text=album_artist)
                audio_file['TRCK'] = TRCK(encoding=3, text=f"{track_number}/{total_tracks}")
                audio_file['TYER'] = TYER(encoding=3, text=release_year)
                audio_file['TCON'] = TCON(encoding=3, text=", ".join(genres).title())
                audio_file['TPOS'] = TPOS(encoding=3, text=disk_number)

                album_art_data = urlopen(album_art).read()
                audio_file['APIC'] = APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=album_art_data
                )
                audio_file.save(v2_version=3)

            elif song.path.endswith(".flac"):
                audio_file = FLAC(song.path)
                audio_file["title"] = song_name
                audio_file["artist"] = ", ".join(song_artists)
                audio_file["album"] = album_name
                audio_file["albumartist"] = album_artist
                audio_file["tracknumber"] = track_number
                audio_file["totaltracks"] = total_tracks
                audio_file["date"] = release_year
                audio_file["genre"] = ", ".join(genres).title()
                audio_file["discnumber"] = disk_number

                album_art_data = urlopen(album_art).read()
                image = Picture()
                image.data = album_art_data
                image.type = 3
                image.mime = "image/jpeg"
                image.desc = "Cover"
                audio_file.clear_pictures()
                audio_file.add_picture(image)
                audio_file.save()

            print(f"Added metadata to {song.artist} - {song.title} successfully!")

        except Exception as e:
            print(f"Error writing metadata to {song.path}: {e}")
            error_list.append(song)

    return error_list, no_genre_list


def get_input_files():
    print("Please select the MP3 or FLAC file(s) you wish to get metadata for.\n"
          "Ensure that the name of each file is in the format: \"Artist Name - Track Name\"\n")
    tkinter.Tk().withdraw()
    return askopenfilenames()


def get_tracks_and_artists(files):
    song_list = []
    wrong_file_extension = []
    wrong_name_format = []

    for file in files:
        head, tail = os.path.split(file)

        if not (tail.endswith(".mp3") or tail.endswith(".flac")):
            wrong_file_extension.append(file)
            continue

        try:
            if tail.endswith(".mp3"):
                track_name = tail[tail.index("-") + 1: tail.index(".mp3")].strip()
            else:
                track_name = tail[tail.index("-") + 1: tail.index(".flac")].strip()

            artist_name = tail[:tail.index("-")].strip()
            song_list.append(Song(track_name, artist_name, file))
        except ValueError:
            wrong_name_format.append(file)

    return song_list, wrong_file_extension, wrong_name_format


def exit_routine():
    print("Press the \"Q\" key to quit.")
    while True:
        if keyboard.is_pressed("q"):
            sys.exit(0)


main()