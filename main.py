import datetime
import logging
import os
import re
import tempfile
from urllib.parse import urlparse

import instaloader
import requests
from telegram import MessageEntity, InputMediaPhoto, InputMediaVideo
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


INSTALOADER = instaloader.Instaloader()


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

def _download(post, filename):
    logging.debug(f"Downloading {post}")
    with tempfile.TemporaryDirectory() as dirname:
        prefix = ''
        if post.is_video:
            prefix = 'video_'
        elif not isinstance(post, instaloader.Post):
            prefix = 'display_'

        url = getattr(post, f'{prefix}url')
        INSTALOADER.download_pic(f'{dirname}/{filename}', url, datetime.datetime.now())
        logging.debug("Post has been downloaded")
        urlmatch = re.search('\\.[a-z0-9]*\\?', url)
        file_extension = url[-3:] if urlmatch is None else urlmatch.group(0)[1:-1]
        with open(f'{dirname}/{filename}.{file_extension}', 'rb') as f:
            if post.is_video:
                return InputMediaVideo(f)
            else:
                return InputMediaPhoto(f)

def download_url(update, context):
    parsed_url = urlparse(update.message.text.strip())
    shortcode = parsed_url.path.strip('/').split('/')[-1]
    post = instaloader.Post.from_shortcode(INSTALOADER.context, shortcode)

    download_original = True
    media_list = []
    for i, node in enumerate(post.get_sidecar_nodes()):
        download_original = False
        media_list.append(_download(node, i))
    
    if download_original:
        media_list.append(_download(post, 'post'))

    logging.debug("Media downloaded, sending")
    update.message.reply_media_group(media_list)
    logging.debug("Media sent")

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    user = os.environ.get('IG_USER')
    passwd = os.environ.get('IG_PASSWD')
    INSTALOADER.login(user, passwd)
    
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
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