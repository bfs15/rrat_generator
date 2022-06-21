# bot.py
from logging import exception
import os

import discord
from dotenv import load_dotenv
import json
from queue import Queue

from consume_requests import requests_queue, stop_event, consume_requests

keyword_complete = "!rrat"
help_string = f"""example: `{keyword_complete} "context": "GPT will complete the text in the context field. The parameters can be adjusted", "max_length": 70, "top_p": 0.9, "top_k": 0, "temperature": 0.75`\nwill return with 🛑 when request queue is full"""
keyword_help = "!rrat help"

discord_env_filepath = "DISCORD.env"
discord_token_var = "DISCORD_TOKEN"
load_dotenv(discord_env_filepath)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client = discord.Client()


@client.event
async def on_ready():
    for guild in client.guilds:
        print(
            f"{client.user} is connected to the following guild:\n"
            f"{guild.name}(id: {guild.id})"
        )


import functools
import typing
import asyncio


def to_thread(func: typing.Callable):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, func)

    return wrapper


def parse_request_message_content(msg_content):
    parameters = msg_content.split(keyword_complete)[-1]
    parameters.strip()
    if not parameters.startswith("{"):
        parameters = "{" + parameters + "}"

    if '"context":' not in parameters:
        parameters = '{"context": ' + parameters[1:]
    return json.loads(parameters, strict=False)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(keyword_help):
        await message.reply(help_string)
        return

    if message.content.startswith(keyword_complete):
        if requests_queue.qsize() > 100:
            await message.add_reaction("🛑")
            return
        # react to message while preparing response
        await message.add_reaction("⌛")
        try:
            parameters = parse_request_message_content(message.content)
            if parameters:
                response_queue = Queue()

                requests_queue.put((parameters, response_queue))

                @to_thread
                def blocking_func():
                    return response_queue.get()

                response = str(json.dumps(await blocking_func(), indent=2))

                # remove reaction
                await message.remove_reaction("⌛", client.user)
                await message.add_reaction("✅")
                # send response
                await message.reply(response, mention_author=False)
        except Exception as e:
            await message.remove_reaction("⌛", client.user)
            await message.add_reaction("❌")
            await message.reply(str(e) + "\n" + help_string, mention_author=False)
        return


def discord_bot_run():
    if not DISCORD_TOKEN:
        raise IOError(f"Missing discord token in env file, please define `{discord_token_var}` in the file {discord_env_filepath}")
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    import threading

    thread_consume_requests = threading.Thread(target=consume_requests)
    thread_consume_requests.start()

    import signal

    def signal_handler(sig, frame):
        global app_running
        stop_event.set()
        thread_consume_requests.join()
        exit(0)


    signal.signal(signal.SIGINT, signal_handler)

    discord_bot_run()