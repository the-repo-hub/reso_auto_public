import time
from configparser import ConfigParser, SectionProxy
from sys import exit
from typing import Optional, Tuple, Dict

from selenium.common.exceptions import NoSuchWindowException, WebDriverException, NoSuchElementException, \
    UnexpectedAlertPresentException, InvalidSessionIdException, InvalidCookieDomainException
from selenium.webdriver import Chrome
from selenium.webdriver import Edge
from selenium.webdriver import Firefox
from selenium.webdriver.chrome.options import ChromiumOptions as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from ResoBot import AccountManager, raise_error


class Browser:
    browserDictionary = {
        'Firefox': [Firefox, FirefoxService, FirefoxOptions],
        'Chrome': [Chrome, ChromeService, ChromeOptions],
        'Edge': [Edge, EdgeService, EdgeOptions]
    }

    def __init__(self, name: str, user_agent: str):
        self.name = name
        try:
            self.klass = self.browserDictionary[name][0]
        except KeyError:
            raise_error(f'Недоступный браузер {name}')
        self.service = self.browserDictionary[name][1]
        self.options = self.browserDictionary[name][2]
        if name == 'Firefox':
            self.options.set_preference("general.useragent.override", user_agent)
        else:
            self.options.add_argument(f"--user-agent='{user_agent}'")


class BrowserMeta(type):

    @staticmethod
    def get_ini_options() -> Optional[SectionProxy]:
        ini_options = ConfigParser()
        result = ini_options.read('reso.ini', encoding='UTF-8')
        # нет файла
        if not result:
            raise_error("Не найден файл reso.ini")
        try:
            options = ini_options['options']
        except KeyError:
            raise_error("Проблемы с ини-файлом, не найдено поле options")
        else:
            for line in options:
                if line != 'hash' or line != 'browser' or line != 'user-agent':
                    raise_error(f'Проблемы с ини-файлом, поле {line} не валидно')
            return options

    def __new__(cls, name: str, bases: Tuple, attrs: Dict):
        options = cls.get_ini_options()
        browser = Browser(name=options['browser'], user_agent=options['user-agent'])
        attrs.update(
            {
                'service': browser.service,
                'options': browser.options,
                'ini_options': options,
            }
        )
        bases = (browser.klass,)
        return super().__new__(cls, name, bases, attrs)


class ResoBrowser(Firefox, metaclass=BrowserMeta):

    url_main = 'https://office.reso.ru/'
    manager = AccountManager()

    # will fill in meta:
    ini_options = Dict
    service = None
    options = None

    def __init__(self):
        super().__init__(service=self.service, options=self.options)
        self.need_to_set_telegram_cookies = False
        self.hash = self.ini_options['hash']
        self.last_cookies = self.manager[self.hash]
        if not self.last_cookies:
            self.quit()
            raise_error('Невалидный хэш')

    def delete_reso_cookies(self):
        self.delete_cookie('ASP.NET_SessionId')
        self.delete_cookie('ResoOffice60')

    def get_and_insert_cookies(self):
        tele_cookies = self.manager[self.hash]
        if not tele_cookies:
            self.quit()
            raise_error('Невалидный хэш')
        self.delete_reso_cookies()
        for line in tele_cookies:
            self.add_cookie(line)

    def find_element(self, *args, **kwargs):
        try:
            return super().find_element(*args, **kwargs)
        except NoSuchElementException:
            return None

    def auth_complete(self):
        if 'reso.ru' in self.current_url and self.url_main + 'login' not in self.current_url:
            welcome = self.find_element(By.XPATH,
                                        '/html/body/form/div[4]/div[1]/div[7]/div/div/div/div/div[1]')  # welcome msg
            qr = self.find_element(By.XPATH, '//*[@id="qrImage"]')  # qr
            if not welcome and not qr:
                return True
        return False

    def get_cookies(self):
        cookies = {
            'ASP.NET_SessionId': self.get_cookie('ASP.NET_SessionId'),
            'ResoOffice60': self.get_cookie('ResoOffice60')
        }
        if cookies.get('ResoOffice60'):
            cookies['ResoOffice60'].pop('domain')
            cookies['ResoOffice60']['sameSite'] = 'None'
        if cookies.get('ASP.NET_SessionId'):
            cookies['ASP.NET_SessionId'].pop('domain')
            cookies['ASP.NET_SessionId']['sameSite'] = 'None'
        return cookies

    def logged_in(self):
        tele_cookies = self.manager[self.hash]
        browser_cookies = self.get_cookies()

        if self.need_to_overwrite_cookies and None not in get:
            self.manager[self.hash] = self.get_cookies()
            self.need_to_overwrite_cookies = False

        if not tele_cookies:
            self.quit()
            raise_error('Невалидный хэш')

        elif self.last_cookies != get:
            self.manager[self.hash] = get
            self.last_cookies = get

        elif get != tele_cookies:
            self.delete_reso_cookies()
            for line in tele_cookies:
                self.add_cookie(line)
            self.last_cookies = self.get_cookies()

    def logged_out(self):
        tele_cookies = self.manager[self.hash]
        if not tele_cookies:
            self.quit()
            raise_error('Невалидный хэш')
        elif self.last_cookies != tele_cookies:
            self.get_and_insert_cookies()
            self.last_cookies = tele_cookies

    def run(self) -> None:
        self.get(self.url_main)
        self.get_and_insert_cookies() # without refreshing
        self.get(self.url_main)
        while True:
            if self.auth_complete():
                self.logged_in()
            else:
                self.logged_out()
            time.sleep(1)



if __name__ == '__main__':
    with ResoBrowser() as r:
        r.run()
