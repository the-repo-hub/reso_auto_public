"""Error handlers and decorators for program."""

import time
from typing import Any, Callable, Dict, Optional, Tuple

from selenium.common.exceptions import (
    InvalidCookieDomainException, InvalidSessionIdException, NoSuchWindowException, UnexpectedAlertPresentException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from telebot.apihelper import ApiTelegramException
from urllib3.exceptions import MaxRetryError


def retry(fn: Callable) -> Callable:
    """Retry decorator for handle errors.

    Args:
        fn: function that will be wrapped.

    Returns:
        Decorator closure.
    """

    def inner(*args: Tuple, **kwargs: Dict) -> Optional[Callable]:
        """Inner decorator function.

        Args:
            args: Tuple with any values.
            kwargs: Dictionary with any variables and values.
        """
        err_counter = 0
        err_type = ''
        while err_counter <= 10:
            try:
                return fn(*args, **kwargs)

            # проблемы с интернетом
            except ConnectionError:
                err_counter += 1
                err_type = 'ConnectionError'

            # проблемы с интернетом для браузера
            except WebDriverException:
                err_counter += 1
                err_type = 'WebDriverException'

            # проблемы с телеграмом
            except ApiTelegramException:
                err_counter += 1
                err_type = 'ApiTelegramException'

            time.sleep(2)
        raise_error(
            'Проблемы с интернетом.\nТип ошибки: {err_type}\nФункция: {name}'.format(
                err_type=err_type, name=fn.__name__,
            ),
        )
        return None

    return inner


def exception_run_handler(fn: Callable) -> Callable:
    """Run function exception handler that.

    Args:
        fn: function that will be wrapped.
    """

    def inner(obj: WebDriver, *args: Tuple, **kwargs: Dict) -> Any:
        """Inner decorator function.

        Args:
            obj: ResoBrowser object.
            args: Tuple with any values.
            kwargs: Dictionary with any variables and values.
        """
        try:
            return fn(obj, *args, **kwargs)
        except NoSuchWindowException:
            # raises if first tab was closed
            try:
                obj.switch_to.window(obj.window_handles[0])
            except InvalidSessionIdException:
                obj.quit()
                exit(0)

        except UnexpectedAlertPresentException:
            # raises if browser had js alert
            pass

        except InvalidCookieDomainException:
            pass

        except InvalidSessionIdException:
            exit(0)

        except IndexError:
            obj.quit()
            exit(0)

        except WebDriverException:
            obj.quit()
            exit(0)

        except MaxRetryError:
            exit(0)

    return inner


def raise_error(error_txt: str) -> Any:
    """Raise window with error."""
    # TODO ctype for windows
    print(error_txt)
    return exit(1)
