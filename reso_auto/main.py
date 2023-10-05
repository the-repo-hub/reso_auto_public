import time
from configparser import ConfigParser, SectionProxy
from os import devnull
from typing import Any, Dict, List, Tuple, Type

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome, Edge, Firefox
from selenium.webdriver.chrome.options import ChromiumOptions as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver

from reso_auto.choiches import CookieFields, ErrorMessages
from reso_auto.handlers import exception_run_handler, raise_error
from reso_auto.manager import MessageManager
from reso_auto.settings import INI_FILE_PATH

BaseDriverMeta: Type = type(WebDriver)


class BrowserDetector:
    """Detect browser class and his services and options."""

    browserDictionary = {
        'Firefox': (Firefox, FirefoxService, FirefoxOptions),
        'Chrome': (Chrome, ChromeService, ChromeOptions),
        'Edge': (Edge, EdgeService, EdgeOptions)
    }

    def __init__(self, name: str, user_agent: str):
        self.name = name
        try:
            self.klass = self.browserDictionary[name][0]
        except KeyError:
            raise_error(ErrorMessages.invalid_browser.value.format(browser=self.name))
        self.service = self.browserDictionary[name][1](log_output=devnull)
        self.options = self.browserDictionary[name][2]()
        if isinstance(self.options, FirefoxOptions):
            self.options.set_preference("general.useragent.override", user_agent)
        else:
            self.options.add_argument(f"--user-agent='{user_agent}'")


class BrowserMeta(BaseDriverMeta):
    """Metaclass for detect browser in ini options and change ResoBrowser class inheritance."""

    @staticmethod
    def get_ini_options() -> SectionProxy:
        ini_options = ConfigParser()
        result = ini_options.read(INI_FILE_PATH, encoding='UTF-8')
        # нет файла
        if not result:
            raise_error(ErrorMessages.no_ini.value)
        try:
            options = ini_options['options']
        except KeyError:
            return raise_error(ErrorMessages.no_ini_options.value)
        for field, value in options.items():
            if not (field == 'hash' or field == 'browser' or field == 'user-agent'):
                raise_error(ErrorMessages.invalid_ini_field.value.format(field=field))
            if not options.get(field):
                raise_error(ErrorMessages.invalid_ini_value.value.format(value=value, field=field))
        return options

    def __new__(cls, name: str, bases: Tuple, attrs: Dict) -> Any:
        options = cls.get_ini_options()
        browser = BrowserDetector(name=options['browser'].capitalize(),
                                  user_agent=options['user-agent'].capitalize())  # type: ignore
        new_browser_class = super().__new__(cls, name, (browser.klass,), attrs)
        new_browser_class.hash = options.get('hash', 'None')
        new_browser_class.service = browser.service
        new_browser_class.options = browser.options
        return new_browser_class


class ResoBrowser(Firefox, metaclass=BrowserMeta):
    url_main = 'https://office.reso.ru/'
    manager = MessageManager()

    # will fill in meta:
    hash: str
    service: FirefoxService
    options: FirefoxOptions

    def __init__(self) -> None:
        super().__init__(service=self.service, options=self.options)
        self.need_to_set_telegram_cookies = False
        self.last_cookies = self.manager.get_telegram_cookies(self.hash)
        if isinstance(self.last_cookies, str):
            self.quit()
            raise_error(self.last_cookies)

    def delete_reso_cookies(self) -> None:
        self.delete_cookie(CookieFields.aspnet.value)
        self.delete_cookie(CookieFields.reso_office60.value)

    def get_and_insert_cookies(self) -> None:
        tele_cookies = self.manager.get_telegram_cookies(self.hash)
        if isinstance(tele_cookies, str):
            self.quit()
            raise_error(tele_cookies)
        self.delete_reso_cookies()
        for line in tele_cookies:
            self.add_cookie(line)
        self.last_cookies = tele_cookies

    def auth_complete(self) -> bool:
        try:
            # welcome message
            self.find_element(By.XPATH, '/html/body/form/div[4]/div[1]/div[7]/div/div/div/div/div[1]')
        except NoSuchElementException:
            return True
        return False

    def get_browser_cookies(self) -> List:
        cookies = [
            self.get_cookie(CookieFields.aspnet.value),
            self.get_cookie(CookieFields.reso_office60.value),
        ]
        if all(cookies):
            cookies[0].pop('domain')  # type: ignore
            cookies[1].pop('domain')  # type: ignore
            return cookies
        return raise_error(ErrorMessages.invalid_cookies.value)

    def logged_in(self) -> None:
        tele_cookies = self.manager.get_telegram_cookies(self.hash)
        if isinstance(tele_cookies, str):
            self.quit()
            raise_error(tele_cookies)
        browser_cookies = self.get_browser_cookies()

        if self.need_to_set_telegram_cookies:
            # somebody logged in
            self.manager.set_telegram_cookies(cookies=browser_cookies, hsh=self.hash)
            self.need_to_set_telegram_cookies = False

        elif self.last_cookies != browser_cookies:
            # i'm logged in, but cookies changed by server
            self.manager.set_telegram_cookies(cookies=browser_cookies, hsh=self.hash)
            self.last_cookies = browser_cookies

        elif browser_cookies != tele_cookies:
            # somebody changed cookies, but my cookies is actual
            self.get_and_insert_cookies()

    def logged_out(self) -> None:
        tele_cookies = self.manager.get_telegram_cookies(self.hash)
        if isinstance(tele_cookies, str):
            self.quit()
            raise_error(tele_cookies)
        if self.last_cookies != tele_cookies:
            self.get_and_insert_cookies()
            self.get(self.url_main)
        else:
            self.need_to_set_telegram_cookies = True

    @exception_run_handler
    def run(self) -> None:

        # if it will be removed, don't forget about implicitly wait
        self.get(self.url_main)
        self.get_and_insert_cookies()
        self.get(self.url_main)
        while True:
            if self.auth_complete():
                self.logged_in()
            else:
                self.logged_out()
            time.sleep(1)


if __name__ == '__main__':
    r = ResoBrowser()
    r.run()
