#!/usr/bin/env python3
import argparse
import logging
import re
import shutil

from typing import List, Tuple, Optional 
from pathlib import Path

# Matches a filename with exactly one set of brackets (NUM) in it
copied_file_pattern = re.compile('[^()]*(\(\d+\))[^()]*')

video_formats = {'.mov', '.mp4'}
video_formats |= set(map(lambda x: x.upper(), video_formats))
image_formats = {'.jpeg', '.jpg', '.png', '.heic'}
image_formats |= set(map(lambda x: x.upper(), image_formats))

def all_media_files(dir: Path) -> List[Path]:
    assert dir.exists()
    res = []
    def recur(dir: Path) -> None:
        assert dir.is_dir()
        for child in dir.iterdir():
            if child.is_dir():
                recur(child)
            elif child.suffix == '.json' or child.name.startswith('.'):
                pass
            else:
                res.append(child)
    recur(dir)
    return res

def corresponding_json(media: Path) -> Optional[Path]:
    # the .json files appear to have a 51 char limit, and they just truncate the prefix
    possible_names = [
        media.name[:46],
        media.name.replace('-edited', '')[:46],
    ]

    match = copied_file_pattern.match(media.name)
    if match is not None:
        brackets = match.group(1)
        possible_names.append(
            media.name.replace(brackets, '')[:46] + brackets
        )

    # live photo's video component
    if media.suffix in video_formats:
        for image_format in image_formats:
            possible_names.append(
                (media.stem + image_format)[:46]
            )


    for name in possible_names:
        candidate = media.with_name(name + '.json')
        if candidate.exists():
            return candidate
    return None

def main():
    logging.basicConfig(level='INFO', format='[%(levelname)s] (%(asctime)s) : %(message)s')
    parser = argparse.ArgumentParser()
    parser.add_argument('google_photos_folder', type=str)
    args = parser.parse_args()
    folder = Path(args.google_photos_folder).resolve()
    media_files : List[Path] = all_media_files(folder)
    logging.info('%s', f'found %{len(media_files)} media files')
    media_and_json : List[Tuple[Path, Optional[Path]]] = list(map(lambda x: (x, corresponding_json(x)), media_files))
    for media, json in media_and_json:
        if not json:
            logging.warning('%s', f"Couldn't find corresponding JSON of {str(media)}")
            continue
        # just throw .json to the end of the media name, so the exiftool command will work
        canonical_json = media.with_name(media.name + '.json')
        if json.name != canonical_json.name:
            logging.debug('%s', f'copying {str(json)} -> {str(canonical_json)}')
            shutil.copyfile(json, canonical_json)
    # see https://legault.me/post/correctly-migrate-away-from-google-photos-to-icloud
    logging.info('%s', f'now you can run: exiftool -r -d %s -tagsfromfile "%d/%F.json" "-GPSAltitude<GeoDataAltitude" "-GPSLatitude<GeoDataLatitude" "-GPSLatitudeRef<GeoDataLatitude" "-GPSLongitude<GeoDataLongitude" "-GPSLongitudeRef<GeoDataLongitude" "-Keywords<Tags" "-Subject<Tags" "-Caption-Abstract<Description" "-ImageDescription<Description" "-DateTimeOriginal<PhotoTakenTimeTimestamp" -ext "*" -overwrite_original -progress --ext json "{folder}"')


if __name__ == '__main__':
    main()
