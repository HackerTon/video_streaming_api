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

    return await send_file(file_path, mimetype="application/x-mpegurl", cache_timeout=0)


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
            abs_path = item
            rel_path = abs_path.split("/")[-1]

            # extract the filetype from the rel_path etc..
            # mp4, mkv, mp3...
            file_type = rel_path.split(".")[-1]

            # trancode if the video file is supported
            if file_type in ["mp4", "mkv", "flv", "webm"]:
                # extract name of the video from rel_path
                video_name = "".join(rel_path.split(".")[:-1])

                # set path to videos/something.m8u3
                output_path = os.path.join(OUTPUT_DIRECTORY, f"{video_name}.m8u3")

                print("debug path")
                for line in [rel_path, abs_path, output_path]:
                    print(line)

                if os.path.exists(output_path):
                    print(f"{output_path} existed, Not process!")
                    continue

                v_input = ffmpeg.input(abs_path)
                audio = v_input.audio
                video = v_input.video
                output = ffmpeg.output(
                    audio,
                    video,
                    output_path,
                    f="hls",
                    hls_segment_filename=os.path.join(
                        OUTPUT_DIRECTORY, f"{video_name}_%04d.ts"
                    ),
                    hls_time=4,
                    hls_playlist_type="event",
                    vcodec="copy",
                    acodec="copy",
                )

                key = random.getrandbits(32)

                r.hset(key, mapping={"name": f'{"".join(video_name)}.m8u3', "state": 1})
                ffmpeg.run(output)
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
