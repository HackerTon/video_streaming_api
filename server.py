import asyncio
import os
import random
import redis

import aioredis
import ffmpeg
from quart import Quart, render_template, request, send_file
from quart.json import jsonify
from quart.utils import run_sync

app = Quart(__name__)
app.clients = set()

DIRECTORY = "/home/hackerton/Videos"


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/send")
async def send():
    data = request.args.get("a")

    for queue in app.clients:
        await queue.put(data)

    return jsonify(True)


# @app.route("/<path>")
# async def path(path):
#     return await send_file(
#         f"/home/hackerton/Videos/2021-07-28_20-22-23/{path}",
#         mimetype="application/x-mpegURL",
#     )


@app.route("/routine")
async def routine():
    queue = asyncio.Queue()
    app.clients.add(queue)

    # async generator
    async def send_events():
        while True:
            data = await queue.get()
            yield data

    return send_events()


@app.route("/play/<id>")
async def play(id):
    redis = aioredis.from_url("redis://localhost", decode_responses=True)

    async with redis.client() as conn:
        result = await conn.hmget(str(id), "state")
        result = 0 if result[0] == None else result[0]

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

    # return await send_file(
    #     "/home/hackerton/Videos/2021-07-28_20-22-23/2021-07-28_20-22-23.m3u8",
    #     mimetype="application/x-mpegURL",
    #     as_attachment=False,
    # )


@app.route("/update")
async def update():
    def synchronous():
        # list of all videos path relative to current path
        list_videos = os.listdir(DIRECTORY)

        # transcode video to mp4
        for video_path in list_videos:
            file_type = video_path.split(".")[-1]

            # if dir continue
            # skip this path
            if os.path.isdir(os.path.join(DIRECTORY, video_path)):
                continue

            # run only when the file is not mp4
            if file_type != "mp4":
                abs_path = os.path.join(DIRECTORY, video_path)
                names = video_path.split(".")[:-1]

                # check for existance first
                if os.path.exists(os.path.join(DIRECTORY, "_".join(names))):
                    continue

                # make directory
                os.makedirs(os.path.join(DIRECTORY, "_".join(names)))

                v_input = ffmpeg.input(abs_path)
                audio = v_input.audio
                video = v_input.video
                output = ffmpeg.output(
                    audio,
                    video,
                    os.path.join(DIRECTORY, "_".join(names), f"{''.join(names)}.m3u8"),
                    f="hls",
                    hls_time=4,
                    hls_playlist_type="event",
                )

                key = random.getrandbits(32)
                r = redis.Redis()
                r.hmset(key, {"name": video_path, "state": 1})
                ffmpeg.run(output)
                r.hmset(key, {"name": video_path, "state": 2})

    asyncio.get_running_loop().run_in_executor(None, synchronous)

    return "we are updating the diagram"


# async def main():
#     redis = aioredis.from_url("redis://localhost")

#     await redis.rpush("alan1", "alan")
#     await redis.rpush("alan1", "16")

#     print(await redis.lrange("alan1", 0, -1))


if __name__ == "__main__":
    app.run("0.0.0.0")
