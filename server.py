import asyncio
import os
import glob
import random
import sys

import aioredis
import ffmpeg
import redis
from quart import Quart, render_template, request, send_file
from quart.json import jsonify

app = Quart(__name__)
app.clients = set()

try:
    DIRECTORY = os.environ["DIRECTORY"] if os.environ["DIRECTORY"] else sys.exit()
    OUTPUT_DIRECTORY = (
        os.environ["OUTPUT_DIR"] if os.environ["DIRECTORY"] else sys.exit()
    )
except KeyError as e:
    print("Set environment variable DIRECTORY & OUTPUT_DIR!")
    sys.exit()


# route for main screen
@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/tailwind.css")
async def css():
    return await send_file("templates/tailwind.css")


# route for video segment path
@app.route("/videos/<path>")
async def path(path):
    file_path = os.path.join(OUTPUT_DIRECTORY, path)

    return await send_file(file_path, mimetype="application/x-mpegurl", cache_timeout=1)


# route for all keys
@app.route("/list")
async def list_all():
    tredis = aioredis.from_url("redis://localhost", decode_responses=True)
    keys = await tredis.keys()
    items = [await tredis.hgetall(key) for key in keys]

    return jsonify(items)


# route to get the playlist
@app.route("/play/<id>")
async def play(id):
    redis = aioredis.from_url("redis://localhost", decode_responses=True)

    async with redis.client() as conn:
        data = await conn.hgetall(str(id))
        print(data)
        # result = 0 if result[] == None else result[0]

    # 0 = new not in server
    # 1 = processing
    # 2 = ready
    if result == 0:
        return "this is new"
    elif result == 1:
        return "please wait processing"
    elif result == 2:
        # ready file of the particular m3u8
        pass
    else:
        raise Exception("internal server error")

    # return the video playlist
    return await send_file(
        "/home/hackerton/Videos/2021-07-28_20-22-23/2021-07-28_20-22-23.m3u8",
        mimetype="application/x-mpegURL",
        as_attachment=False,
        cache_timeout=1,
    )


def split_parts_probe(path):
    probe = ffmpeg.probe(path)
    video = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
    audio = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
    subtitle = [
        stream for stream in probe["streams"] if stream["codec_type"] == "subtitle"
    ]

    return video, audio, subtitle


def rename_file_if(path: str):
    # if the file contain space
    if " " in path:
        # replace space with underscore
        new_path = path.replace(" ", "_")

        try:
            os.rename(path, new_path)
        except NotImplementedError:
            print("Renaming file unsupported contact programmer.")

        return new_path

    return path


# command to update all videos
@app.route("/update")
async def update():
    def synchronous():
        r = redis.Redis()
        supported = ["mkv", "mp4"]
        items = []

        for container in supported:
            items += glob.glob(f"{DIRECTORY}/**/*.{container}", recursive=True)

        for item in items:
            abs_path = rename_file_if(item)
            rel_path = abs_path.split("/")[-1]

            m_video, m_audio, m_subtitle = split_parts_probe(abs_path)

            # extract name of the video from rel_path
            video_name = "".join(rel_path.split(".")[:-1])
            # set path to videos/something.m8u3
            output_path = os.path.join(OUTPUT_DIRECTORY, f"{video_name}.m8u3")

            # print("debug path")
            # for line in [rel_path, abs_path, output_path]:
            #     print(line)

            if os.path.exists(output_path):
                print(f"{output_path} existed, Not process!")
                continue

            v_input = ffmpeg.input(abs_path, init_hw_device="qsv=hw")
            video = v_input.video
            vcodec = "copy"
            acodec = "copy"

            audio = v_input["a:0"]

            if m_audio[0]["codec_name"] != "aac":
                acodec = "aac"

            # if subtitle is built-in
            # embedded subtitle into video
            # must transcode
            if len(m_subtitle):
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
                    vf=f"subtitles={abs_path},hwupload=extra_hw_frames=64,format=qsv",
                    vcodec=vcodec,
                    acodec=acodec,
                    q=20,
                    audio_bitrate="128k",
                    ac=2,
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
                )

            key = random.getrandbits(32)

            r.hset(key, mapping={"name": f'{"".join(video_name)}.m8u3', "state": 1})

            try:
                ffmpeg.run(output)
            except ffmpeg._run.Error as e:
                print(f"Error Message -> {e.stdout}")
                print(f"{video_name} unable to process due to certain error")

            r.hset(key, mapping={"name": f'{"".join(video_name)}.m8u3', "state": 2})

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
    app.run("0.0.0.0")
