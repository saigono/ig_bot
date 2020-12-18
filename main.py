import datetime
import os
import re
import tempfile
from urllib.parse import urlparse

import instaloader
import requests
from telegram import MessageEntity
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


INSTALOADER = instaloader.Instaloader()


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

def _download_and_reply(update, post, filename):
    with tempfile.TemporaryDirectory() as dirname:
        prefix = ''
        if post.is_video:
            prefix = 'video_'
        elif not isinstance(post, instaloader.Post):
            prefix = 'display_'

        url = getattr(post, f'{prefix}url')
        INSTALOADER.download_pic(f'{dirname}/{filename}', url, datetime.datetime.now())
        urlmatch = re.search('\\.[a-z0-9]*\\?', url)
        file_extension = url[-3:] if urlmatch is None else urlmatch.group(0)[1:-1]
        with open(f'{dirname}/{filename}.{file_extension}', 'rb') as f:
            if post.is_video:
                update.message.reply_video(f)
            else:
                update.message.reply_photo(f)

def download_url(update, context):
    parsed_url = urlparse(update.message.text.strip())
    shortcode = parsed_url.path.strip('/').split('/')[-1]
    post = instaloader.Post.from_shortcode(INSTALOADER.context, shortcode)

    download_original = True
    for i, node in enumerate(post.get_sidecar_nodes()):
        download_original = False
        _download_and_reply(update, node, i)
    
    if not download_original:
        return

    _download_and_reply(update, post, 'post')


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    download_handler = MessageHandler(
        Filters.text & (Filters.entity(MessageEntity.URL) | Filters.entity(MessageEntity.TEXT_LINK)), 
        download_url
    )
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(download_handler)
    updater.start_polling()

if __name__ == '__main__':
    main()