import asyncio
import glob
import os
import random
import re
import sys
import logging

import aioredis
import ffmpeg
import redis
from quart import Quart, render_template, request, send_file
from quart_cors import cors
from quart.json import jsonify

app = Quart(__name__)
app = cors(app)

try:
    DIRECTORY = os.environ["DIRECTORY"] if os.environ["DIRECTORY"] else sys.exit()
    OUTPUT_DIRECTORY = (
        os.environ["OUTPUT_DIR"] if os.environ["DIRECTORY"] else sys.exit()
    )
except KeyError as e:
    print("Set environment variable DIRECTORY & OUTPUT_DIR!")
    logging.info("Set environment variable DIRECTORY & OUTPUT_DIR!")
    sys.exit()


# route for main screen
# @app.route("/")
# async def index():
#     return await render_template("index.html")

# @app.route("/tailwind.css")
# async def css():
#     return await send_file("templates/tailwind.css", cache_timeout=0)


# @app.route("/script.js")
# async def script():
#     return await send_file("templates/script.js", cache_timeout=0)


# route for video segment path
# @app.route("/videos/<path>")
# async def path(path):
#     file_path = os.path.join(OUTPUT_DIRECTORY, path)
#     return await send_file(file_path, mimetype="application/x-mpegurl")


# @app.route("/sushibb")
# async def sushibb():
#     return await render_template()


# route for all keys
@app.route("/list")
async def list_all():
    tredis = aioredis.from_url("redis://myredis", decode_responses=True)
    keys = await tredis.hgetall("movie")
    items = [
        await tredis.hgetall(key)
        for key in keys
        if await tredis.hget(key, "state") == "2"
    ]

    return jsonify(items)


def split_parts_probe(path):
    probe = ffmpeg.probe(path)
    video = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
    audio = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
    subtitle = [
        stream for stream in probe["streams"] if stream["codec_type"] == "subtitle"
    ]

    return video, audio, subtitle


def rename_file_if(path: str):
    # perform substitution if contain -> []whitespace
    new_path = re.sub(r"[\[\],]|\s", "_", path)

    # if the file contain space
    if new_path != path:
        try:
            os.rename(path, new_path)
        except NotImplementedError:
            print("Renaming file unsupported contact programmer.")
            logging.info("Renaming file unsupported contact programmer.")

        return new_path

    return path


# command to update all videos
@app.route("/update")
async def update():
    def synchronous():
        r = redis.Redis(host="myredis", port=6379, decode_responses=True)

        # only allow on one synchronous operation to run
        if r.hget("system", "status") == "1":
            return

        r.hset("system", mapping={"status": 1})

        supported = ["mkv", "mp4"]
        videos = []

        for container in supported:
            # file path of each video files
            videos += glob.glob(f"{DIRECTORY}/**/*.{container}", recursive=True)

        for video in videos:
            abs_path = rename_file_if(video)
            rel_path = abs_path.split("/")[-1]

            try:
                m_video, m_audio, m_subtitle = split_parts_probe(abs_path)
            except ffmpeg.Error as e:
                logging.error(f"Skip {abs_path}")
                continue

            # extract name of the video from rel_path
            video_name = "".join(rel_path.split(".")[:-1])
            # set output path to videos/something.m8u3
            output_path = os.path.join(OUTPUT_DIRECTORY, f"{video_name}.m8u3")

            debug = {}
            # print("debug path")
            # for line in [rel_path, abs_path, output_path]:
            #     print(line)
            debug = {"ss": 0, "t": 120}

            if os.path.exists(output_path):
                logging.info(f"{output_path} exited, Not process!")
                continue

            v_input = ffmpeg.input(abs_path, init_hw_device="qsv=hw")
            video = v_input.video
            vcodec = "copy"
            acodec = "copy"
            audio = v_input["a:0"]
            p_state = -1

            # if subtitle is built-in
            # embedded subtitle into video
            # must transcode
            if len(m_subtitle):
                stream_idx = None

                # grab the subtitle stream that comes first
                # means 1 is chosen instead of 2
                for subtitle in m_subtitle:
                    if subtitle["codec_name"] in ["srt", "ass"]:
                        stream_idx = subtitle["index"]
                        break

                if stream_idx:
                    p_state = 0

            # set vcodec to h264 if not h264
            if m_video[0]["codec_name"] != "h264":
                p_state = 2

            # set codec to acc if not acc
            if m_audio[0]["codec_name"] != "aac":
                acodec = "aac"

            # p_state == 0; transcode with subtitles
            # p_state == 1; transcode audio only
            # p_state == 2; transcode video to h264
            # else direct copy video and audio

            if p_state == 0:
                video = video.filter("subtitles", f"{abs_path}", si=stream_idx)
                video = video.filter("hwupload", extra_hw_frames=64)
                video = video.filter("format", "qsv")
                vcodec = "h264_qsv"
                output = ffmpeg.output(
                    video,
                    audio,
                    output_path,
                    f="hls",
                    hls_segment_filename=os.path.join(
                        OUTPUT_DIRECTORY, f"{video_name}_%04d.ts"
                    ),
                    hls_time=6,
                    hls_playlist_type="event",
                    vcodec=vcodec,
                    acodec=acodec,
                    global_quality=20,
                    audio_bitrate="128k",
                    ac=2,
                    **debug,
                )
            elif p_state == 2:
                video = video.filter("hwupload", extra_hw_frames=64)
                video = video.filter("scale_qsv", w=1920, h=1080, format="nv12")
                vcodec = "h264_qsv"
                output = ffmpeg.output(
                    video,
                    audio,
                    output_path,
                    f="hls",
                    hls_segment_filename=os.path.join(
                        OUTPUT_DIRECTORY, f"{video_name}_%04d.ts"
                    ),
                    hls_time=6,
                    hls_playlist_type="event",
                    preset="veryfast",
                    vcodec=vcodec,
                    acodec=acodec,
                    global_quality=20,
                    audio_bitrate="128k",
                    ac=2,
                    **debug,
                )
            else:
                output = ffmpeg.output(
                    video,
                    audio,
                    output_path,
                    f="hls",
                    hls_segment_filename=os.path.join(
                        OUTPUT_DIRECTORY, f"{video_name}_%04d.ts"
                    ),
                    hls_time=6,
                    hls_playlist_type="event",
                    vcodec=vcodec,
                    acodec=acodec,
                    audio_bitrate="128k",
                    ac=2,
                    **debug,
                )

            key = random.getrandbits(32)
            # add into movie list
            r.hset("movie", key, f'{"".join(video_name)}.m8u3')

            # add to our hash
            r.hset(
                key,
                mapping={
                    "name": f'{"".join(video_name)}.m8u3',
                    "state": 1,
                    "description": "is a movie",
                },
            )

            try:
                output = output.global_args("-hide_banner")
                print(ffmpeg.compile(output))
                ffmpeg.run(output)
                r.hset(key, mapping={"name": f'{"".join(video_name)}.m8u3', "state": 2})
            except ffmpeg.Error as e:
                logging.error(f"Error Message -> {e.stderr}")
                logging.error(f"{video_name} unable to process due to certain error")

                # delete keys
                r.hdel("movie", key)
                r.hdel(key, "name", "state")

        r.hset("system", mapping={"status": 0})

    asyncio.get_running_loop().run_in_executor(None, synchronous)
    return "we are updating all videos"


@app.route("/debug")
async def debug():
    def sync():
        # find supported video stream
        supported = ["mkv", "mp4"]
        items = []

        for container in supported:
            items += glob.glob(f"{DIRECTORY}/**/*.{container}", recursive=True)

        for item in items:
            print(item)

    asyncio.get_running_loop().run_in_executor(None, sync)

    return "this is just a debug"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        filename="transcoder.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
    )

    app.run("0.0.0.0")
