import json
from typing import Dict, Optional

from telebot import TeleBot

from support import retry


class AccountManager:

    message_sample = {
        'test': {
            'ASP.NET_SessionId':
                {'name': 'ASP.NET_SessionId', 'value': '3D348D62E7F8F979671E3F6696A9AA10BCBB8B8C3B6FA2FF5D936B9BDCA8387323211D393DB87804C5DCCCCCA8549C0B78612EDFFF534224CA62FC0CA1413EA705D0DE177DC858A6B97DBE5FBC3D9BB51A56A0D19CCE4B5A4960811944D19DF274D5B6B3EEE03038B7C83B00E99194F1', 'path': '/', 'secure': False, 'httpOnly': True,
                 'sameSite': 'None', 'domain': 'office.reso.ru'},
            'ResoOffice60':
                {'name': 'ResoOffice60', 'value': 'lbzhaffyeiwv312lkcll2oqh', 'path': '/', 'secure': False, 'httpOnly': True,
                 'sameSite': 'None', 'domain': 'office.reso.ru'},
        }
    }

    def __init__(self) -> None:
        # FIXME token
        self.bot = TeleBot('6418619101:AAHOJH3hc5lz41nA7mB5FMAHUsPgvvR4a7g')
        self.chat = 408972919

    @retry
    def reinit(self) -> None:
        pinned = self.bot.get_chat(self.chat).pinned_message
        if pinned:
            self.bot.edit_message_text(chat_id=self.chat, message_id=pinned.message_id, text=json.dumps(self.message_sample))
        else:
            msg = self.bot.send_message(chat_id=self.chat, text=json.dumps(self.message_sample))
            self.bot.pin_chat_message(chat_id=self.chat, message_id=msg.message_id)

    @retry
    def get_telegram_cookies(self, hsh: str) -> Optional[Dict]:
        pinned = self.bot.get_chat(self.chat).pinned_message
        if not pinned:
            self.reinit()
        try:
            return json.loads(pinned.text)[hsh]
        except KeyError:
            return None

    @retry
    def set_telegram_cookies(self, cookies: Dict, hsh: str) -> None:
        pinned = self.bot.get_chat(self.chat).pinned_message
        as_json = json.loads(pinned.text)
        as_json[hsh] = cookies
        self.bot.edit_message_text(chat_id=self.chat, message_id=pinned.message_id, text=json.dumps(as_json))

    @retry
    def add_account(self, hsh) -> None:
        pinned = self.bot.get_chat(self.chat).pinned_message
        as_json = json.loads(pinned.text)
        as_json[hsh] = self.message_sample
        self.bot.edit_message_text(chat_id=self.chat, message_id=pinned.message_id, text=json.dumps(as_json))

    @retry
    def remove_account(self, hsh) -> None:
        pinned = self.bot.get_chat(self.chat).pinned_message
        as_json = json.loads(pinned.text)
        as_json.pop(hsh)
        self.bot.edit_message_text(chat_id=self.chat, message_id=pinned.message_id, text=json.dumps(as_json))
