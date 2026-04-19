import json
import math
import os
import shlex
import subprocess
import sys
from datetime import timedelta
from itertools import batched
from pathlib import Path
from typing import List

import click
import mlx_whisper


@click.command()
@click.option(
    "--input-file", "-i",
    help="The MP4 video file to process. MUST have an .mp4 file extension.",
)
def main(input_file: str):
    """This is the entrypoint for the script. It processes the CLI flags and
    hands off to other functions for processing.

    Args:
        input_file (string): The input .mp4 file to process.
    """
    raw_filename = Path(input_file)
    if not raw_filename.is_file():
        raise FileNotFoundError(f"Could not find {raw_filename} on disk.")

    try:
        # Convert the video to audio-only.
        convert_video_to_audio(str(raw_filename), raw_filename.stem)
    except Exception as e:
        sys.exit(e)

    video_timestamps = transcribe_audio(raw_filename.stem)
    # pp(video_timestamps)

    video_frames(str(raw_filename), raw_filename.stem, video_timestamps)

def convert_video_to_audio(input_filename: str, output_filename: str):
    """This function simple shells-out to ffmpeg for processing. It converts the
    video input to M4A audio output.

    Args:
        input_filename (string): The input filename, with the file extension.
        output_filename (string): The same input filename, without the file extension.
    """
    out_path = Path("out", output_filename)
    out_file = Path(out_path, f"{output_filename}.m4a")
    os.makedirs(out_path, mode=0o755, exist_ok=True)

    if out_file.is_file():
        print(f"File {out_file} already exists. Skipping.")
        return

    command = f"ffmpeg -i {input_filename} -vn -acodec aac_at -b:a 192k " + \
        f"{out_file} -y -hide_banner"

    print(command)

    subprocess.run(shlex.split(command), check=True)

def format_timestamps(dict, key):
    mostly_right = str(0)+str(
        timedelta(
            seconds=dict[key]
        )
    ).replace(".", ",")

    if "," in mostly_right:
        mostly_right = mostly_right[:-3]
    else:
        mostly_right += ",000"

    return mostly_right

def transcribe_audio(filename: str):
    """_summary_

    Args:
        input_filename (str): _description_
        output_filename (str): _description_

    Returns:
        (str): A string of ffmpeg-formatted timestamps.
    """
    out_path = Path("out", filename)
    print("Running AI transcription task. There will be no output until completion. Please be patient.")

    data = mlx_whisper.transcribe(
        str(Path(out_path, f"{filename}.m4a")),
        path_or_hf_repo="mlx-community/whisper-large-v3-mlx",
        language="en",
        temperature=0,
        length_penalty=0.6,
        best_of=5,
        task="transcribe",
        condition_on_previous_text=False,
        word_timestamps=True,
    )

    # Existing transcription
    # with open("output.json") as f:
    #     data = json.loads(f.read())

    segments = data["segments"]
    vf_select = []

    # https://github.com/openai/whisper/discussions/98#discussioncomment-3725983
    for segment in segments:
        startTime = format_timestamps(segment, "start")
        endTime = format_timestamps(segment, "end")
        text = segment['text'].strip()
        segmentFormatted = f"{startTime} --> {endTime}\n{text}\n"
        print(segmentFormatted)

        # Collect timestamps
        frame_timestamp = math.floor(segment['start'])
        vf_select.append(f"{frame_timestamp}")

    return vf_select

def video_frames(input_filename: str, output_filename: str, vf_select: List[str]):
    """_summary_

    Args:
        input_filename (str): _description_
        output_filename (str): _description_
        vf_select (List[str]): _description_
    """
    out_path = Path("out", output_filename)
    os.makedirs(out_path, mode=0o755, exist_ok=True)
    count = 0

    # ffmpeg can't handle all of these timecodes at once, so we batch them.
    for chunk in batched(vf_select, 100):
        count = count + 1
        vfsel: List[str] = []

        for timecode in chunk:
            vfsel.append(f"eq(t\\,{timecode})")

        command = f"ffmpeg -threads 0 -sws_flags fast_bilinear -i {input_filename} -vf select='{"+".join(vfsel)}' " + \
            "-fps_mode vfr -enc_time_base 0 -y -hide_banner " + str(Path(out_path, f"frame_{count}%02d.jpg"))

        print(command)

        subprocess.run(shlex.split(command), check=True)

if __name__ == '__main__':
    main()
