import os, sys,socket, threading, psutil, time, shutil, pathlib, requests, re, json, subprocess, glob, traceback
import tkinter as tk
from tkinter import messagebox
from logger import Logger as Log
from datetime import date, timedelta, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.relative_locator import locate_with
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException, ElementNotInteractableException, ElementNotVisibleException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional, List, Union, Callable
from webdriver_manager.chrome import ChromeDriverManager

url="https://ecp.mis66.ru/"
users=[{'username':'GIBPlenkin3','password':'GIBPlenkin317'},
       {'username':'GIBPlenkin4','password':'GIBPlenkin417'}]
# username='GIBPlenkin2'
# password='GIBPlenkin217'
today = "03.07.2025"
yesterday = (date.today() - timedelta(days=1)).strftime("%d.%m.%Y")
day_defore_yesterday = (date.today() - timedelta(days=2)).strftime("%d.%m.%Y")
forbidden_ds=['U07.','B20.','B21.','B22.','B23.','C34.','S22.']
tg_token='8068921919:AAFZq04-eejhUxqueKwym3Q6D4vCrpoJrIE'
tg_chat_id='655062942'

window_width='1920'
window_height='2500'
window_zoom='0.4'

class ClickError(Exception):
    def __init__(self, xpath: str):
        self.xpath = xpath
        self.message = f"Failed to click element with xpath: {xpath}"
        super().__init__(self.message)

class DriverManager:
    _driver = None
    _log_entries = None
    _profile_directory_base = os.path.join(os.getcwd(), "ChromeProfiles")
    _profile_directory = "wrong_directory"
    _max_retries = 3
    _num_instance = None
    _username = 'username'
    _password = 'password'
    @classmethod
    def get_driver(cls):
        return cls._driver
    
    @classmethod
    def get_user_credentials(cls):
        return cls._username, cls._password
    
    @classmethod
    def is_browser_alive(cls):
        try:
            return cls._driver is not None and cls._driver.title is not None
        except:
            return False

    @staticmethod
    def _find_free_port():
        from contextlib import closing
        
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = s.getsockname()[1]
            Log.info(f'_find_free_port(): {result}')
            return result

    @classmethod
    def start_driver(cls, url=None, restart=False, num_instance=0):
        cls._num_instance=num_instance
        cls._username = users[num_instance % len(users)]['username']
        cls._password  = users[num_instance % len(users)]['password']
        Log.info(f'DriverManager.start_driver: restart={restart}, url={url}')
        cls._profile_directory = os.path.join(cls._profile_directory_base, f"User_{num_instance}")
        os.makedirs(cls._profile_directory, exist_ok=True)
        # def cleanup_processes():
        #     """Clean up all Chrome and chromedriver processes"""
        #     try:
        #         for proc in psutil.process_iter(['pid', 'name']):
        #             try:
        #                 if proc.info['name'] and 'chrome' in proc.info['name'].lower():
        #                     proc.kill()
        #                     Log.info(f"Killed Chrome process: {proc.info['pid']}")
        #                 elif proc.info['name'] and 'chromedriver' in proc.info['name'].lower():
        #                     proc.kill()
        #                     Log.info(f"Killed chromedriver process: {proc.info['pid']}")
        #             except (psutil.NoSuchProcess, psutil.AccessDenied):
        #                 continue
        #             except Exception as e:
        #                 Log.warning(f"Error killing process {proc.info['pid']}: {str(e)}")
        #     except Exception as e:
        #         Log.warning(f"Error during process cleanup: {str(e)}")
    
        def configure_chrome_options():
            """Configure Chrome options with memory management settings"""
            options = Options()
            if os.path.exists(cls._profile_directory):
                options.add_argument(f"user-data-dir={cls._profile_directory}")
            else:
                os.makedirs(cls._profile_directory, exist_ok=True)
                options.add_argument(f"user-data-dir={cls._profile_directory}")
            options.add_argument(f"--window-title=Бот {cls._num_instance}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument(f"--window-size={window_width},{window_height}")
            options.add_argument(f"--force-device-scale-factor={window_zoom}")
            prefs = {
                "disk-cache-size": 4096,
                "browser.cache.disk.enable": False,
                "browser.cache.memory.enable": True
            }
            options.add_experimental_option("prefs", prefs)
            
            return options
    
        try:
            if restart:
                # cleanup_processes()
                time.sleep(2)
            if not restart and cls._driver is not None:
                try:
                    cls._driver.current_url
                    Log.info("Reusing existing driver instance")
                    if url:
                        cls._driver.get(url)
                    return True
                except Exception:
                    cls._driver = None
                    Log.info("Existing driver not responsive, creating new instance")
            options = configure_chrome_options()
            service = Service(
                ChromeDriverManager().install(),
                log_path=os.path.join(cls._profile_directory, "chromedriver.log")
            )
            for attempt in range(cls._max_retries):
                try:
                    Log.info(f"Starting Chrome (attempt {attempt + 1})")
                    cls._driver = webdriver.Chrome(
                        service=service,
                        options=options
                    )
                    
                    # Configure timeouts
                    cls._driver.set_page_load_timeout(120)
                    cls._driver.set_script_timeout(30)
                    
                    if url:
                        cls._driver.get(url + '?c=portal&m=udp')
                    
                    # Add cleanup handler
                    import atexit
                    atexit.register(cls.cleanup)
                    ensure_extension_installed(cls._driver, cls._profile_directory)
                    cls._driver.execute_script(f'document.title="Экземпляр бота №{cls._num_instance}"')
                    return True
                    
                except Exception as e:
                    Log.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == cls._max_retries - 1:
                        raise WebDriverException(f"Failed after {cls._max_retries} attempts")
                    # cleanup_processes()
                    time.sleep(5 * (attempt + 1))
    
        except Exception as e:
            Log.error(f"Critical error in start_driver: {str(e)}")
            # cleanup_processes()
            raise
    @classmethod
    def cleanup(cls):
        """Clean up resources"""
        try:
            if cls._driver is not None:
                cls._driver.quit()
        except Exception:
            pass
        finally:
            cls._driver = None
        # cleanup_processes()



def ensure_extension_installed(driver, profile_dir):
    extension_id = "pfhgbfnnjiafkhfdkmpiflachepdcjod"  # ID расширения КриптоПро ЭЦП (раньше было iifchhfnnmpdbibifmljnfjhpififfog)
    manifest_file = os.path.join(profile_dir, "Default/Extensions", extension_id, "*", "manifest.json")
    if glob.glob(manifest_file):
        return True
    else:
        driver.execute_script("window.open('https://chrome.google.com/webstore/detail/%s');" % extension_id)
        root = tk.Tk()
        root.withdraw()  # Скрываем основное окно Tkinter
        messagebox.showinfo("Установка расширения",
                           f"Ваш профиль:\n{profile_dir}\n\n"
                           f"Установите расширение \"КриптоПро ЭЦП\". "
                           f"После установки нажмите OK.")
        # root.mainloop()
        return True
def add_one_day(date_str):
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    next_date = date_obj + timedelta(days=1)
    result = next_date.strftime("%d.%m.%Y")
    Log.info(f"Вычислена новая дата {result}")
    return result
def generate_level_ups(num):
    text=''
    for i in range(num):
        text+="/.."
    return text
def waiting(times=10):
    Log.info(f'waiting {times} times')
    print('waiting', end='')
    for i in range(times):
        try:
            start_time = time.time()
            wait = WebDriverWait(DriverManager.get_driver(), 60)
            wait.until(lambda _: DriverManager.get_driver().execute_script("return jQuery.active == 0"))
            elapsed = time.time() - start_time
            if elapsed > 0.5:
                print('+', end='')
            else:
                print('.', end='')
        except Exception as e:
            print('x', end='')
        time.sleep(0.5)
    print('!')
def click_xpath(xpath: str, wait: int = 10, crit: bool = True) -> bool:
    Log.info(f"click_xpath: xpath={xpath}, crit={crit}, wait={wait}")
    JS_CHECK_ELEMENT = """
    const elem = arguments[0];
    try {
        if (!elem || !elem.getBoundingClientRect) return false;
        const rect = elem.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        
        // Basic visibility check
        if (!(rect.width > 0 && rect.height > 0)) return false;
        
        // Viewport check with tolerance
        const buffer = 5; // 5px tolerance
        const inViewport = (
            rect.top >= -buffer &&
            rect.left >= -buffer &&
            rect.bottom <= buffer + 10000 && // (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= buffer + 10000 //(window.innerWidth || document.documentElement.clientWidth)
        );

        // Not covered check
        const elementAtPoint = document.elementFromPoint(x, y);
        return inViewport && elementAtPoint === elem || elem.contains(elementAtPoint);
    } catch(e) {
        return false;
    }
    """
    def is_element_clickable(element):
        try:
            if not (element.is_displayed() and element.is_enabled()):
                return False
            return DriverManager.get_driver().execute_script(JS_CHECK_ELEMENT, element)
        except (ElementNotVisibleException, ElementNotInteractableException):
            return False
        except Exception as e:
            Log.warning(f"Error checking element: {str(e)}")
            return False
            
    def wait_for_clickable_elements(xpath, crit=False, max_attempts=3, delay=1):
        for attempt in range(max_attempts):
            all_elements = DriverManager.get_driver().find_elements(By.XPATH, xpath)
            clickable_elements = [elem for elem in all_elements if is_element_clickable(elem)]
            if clickable_elements:
                return clickable_elements
            if attempt < max_attempts - 1:  # Don't sleep on the last iteration
                time.sleep(delay)
        if crit:
            Log.info(f"No clickable elements found for XPath: {xpath}")
            raise ClickError(f"No clickable elements found for XPath: {xpath}")
        return []
    clickable_elements = wait_for_clickable_elements(xpath, crit, max_attempts=wait, delay=1)
    if clickable_elements:
        for element in clickable_elements:
            try:
                element.click()
                Log.info('CLICK!')
                waiting(times=2)
                return element#True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                Log.info(f"click_xpath intercepted: crit={crit}, xpath={xpath}")
                time.sleep(1)
                if crit:
                    for attempt in range(3):
                        if click_xpath(xpath, wait=1, crit=False):
                            Log.info('CLICK!')
                            return element#True
                        time.sleep(2 ** attempt)  # Exponential backoff
                    Log.warning(f"!!!!!!!!!!ClickError Exception!!!!!!!!!! crit={crit}, xpath={xpath}")
                    raise ClickError(xpath)
                return False
            except TimeoutException:
                Log.warning(f"!!!!!!!!!!click_xpath timeout!!!!!!!!!! crit={crit}, xpath={xpath}")
                if crit:
                    raise ClickError(xpath)
                return False
    if crit:
        raise ClickError(xpath)
    return False
def type_xpath(xpath,string,wait=10):
    Log.info(f'typing, string={string}, xpath={xpath}')
    element = WebDriverWait(DriverManager.get_driver(),wait).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    time.sleep(0.3)
    element.clear()
    time.sleep(0.3)
    element.send_keys(string)
    time.sleep(1)
    return True
def click_id(id, wait=10, crit=True):
    xpath = "//*[@id='"+id+"']"
    return click_xpath(xpath, wait=wait, crit=crit)
def click_text(text,level_ups=0, wait=10, crit=True, contains=True):
    if contains:
        xpath = "//*[contains(text(),'"+ text+"')]"+generate_level_ups(level_ups)
    else:
        xpath = "//*[text()='"+ text+"']"+generate_level_ups(level_ups)
    return click_xpath(xpath, wait=wait, crit=crit)
def click_class(text, wait=10, crit=True, count=0):
    if count==0:
        number=""
    else:
        number="["+str(count)+"]"
    xpath = "(//*[contains(@class,'"+text+"')]"+number+")"
    return click_xpath(xpath, wait=wait, crit=crit)
def hover_n_click_text(text, wait=10, crit=True):
    Log.info(f"hover and click text, crit={crit}, text={text}")
    xpath = "//*[text()='"+ text+"']/../.."
    counter=0
    while True:
        try:
            elements = DriverManager.get_driver().find_elements(By.XPATH, xpath)
            for element in elements:
                if element.is_enabled() and element.is_displayed() and element.location['x']>0 and element.location['y']>0:
                    ActionChains(DriverManager.get_driver()).move_to_element(element).perform()
                    time.sleep(1)
                    element.click()
                    time.sleep(1)    
                    return True
                    break
        except (ElementClickInterceptedException, StaleElementReferenceException, ElementNotInteractableException):
            Log.warning(f"click_xpath intercepted, crit={crit}, xpath={xpath}")
            time.sleep(1)
            counter+=1
            if counter>2:
                if crit==True:
                    raise ClickError(xpath)
                return False
        counter+=1
        if counter>2:
            return False
def sendesc():
    webdriver.ActionChains(DriverManager.get_driver()).send_keys(Keys.ESCAPE).perform()
def get_element_value(xpath):
    wait = WebDriverWait(DriverManager.get_driver(), 10)
    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    return element.get_attribute("value")
def logout():
    click_xpath("//*[@class='dijitReset dijitInline dijitIcon balanceApplicationTitleCloseButton']")
    DriverManager.get_driver().quit()
    Log.info('Logout sequence completed')
    waiting()
def scroll_element_to_bottom(element_xpath):
    driver = DriverManager.get_driver()
    wait = WebDriverWait(driver, 10)
    element = wait.until(EC.presence_of_element_located( (By.XPATH, element_xpath) ))
    last_height = driver.execute_script("return arguments[0].scrollHeight", element)
    while True:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
        waiting(2)
        new_height = driver.execute_script("return arguments[0].scrollHeight", element)
        if new_height == last_height:
            break
        last_height = new_height
def login():
    if url+"?c=promed" in DriverManager.get_driver().current_url:
        Log.info("Already logined")
        return True
    Log.info('----------login------------')
    while not url+"?c=promed" in DriverManager.get_driver().current_url:
        username,password=DriverManager.get_user_credentials()
        Log.info(f"current url is {DriverManager.get_driver().current_url} trying to login with {username}")
        type_xpath("//*[@id='promed-login']",username)
        type_xpath("//*[@id='promed-password']",password)
        click_text('Войти',wait=3, crit=False, contains=False)
        waiting()
        DriverManager.get_driver().refresh()
    Log.info("current url is {DriverManager.get_driver().current_url} login completed")
    waiting()
def select_arm(max_attempts=10):
    Log.info('----------select_arm------------')
    attempts = 0
    while not click_xpath("//span[text()='Журнал приемного отделения']", wait=10, crit=False):
        attempts += 1
        if attempts >= max_attempts:
            Log.warning("Emergency exit: Maximum attempts reached")
            return False
        click_xpath("//a[@id='header_link_swMPWorkPlacePriemWindow']", wait=10, crit=False)
        # click_xpath("//*[contains(@id,'header_link_swMPWorkPlace')]", wait=10, crit=False)
        if click_text("АРМ врача приемного отделения (ExtJS 6)", wait=10, crit=False, contains=True):
            Log.info("ARM clicked")
            waiting() 
        waiting()
    Log.info("ARM selected")
    waiting()
    return True
def send_telegram_alert(message, screenshot=None):
    """
    Send message and optionally screenshot to Telegram bot
    """
    message_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    message_payload = {
        'chat_id': tg_chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(
            message_url,
            data=json.dumps(message_payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code != 200:
            Log.warning(f"Telegram message API error: {response.text}")
        
        if screenshot:
            photo_url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
            files = {'photo': ('screenshot.png', screenshot, 'image/png')}
            data = {'chat_id': tg_chat_id}
            
            photo_response = requests.post(
                photo_url,
                files=files,
                data=data,
                timeout=15
            )
            if photo_response.status_code != 200:
                Log.warning(f"Telegram photo API error: {photo_response.text}")
        return True
    except requests.exceptions.RequestException as e:
        Log.warning(f"Failed to send Telegram alert: {e}")
        return False
def click_with_counter(while_func, while_func_args, body_func, body_func_args, exit_func, exit_func_args):
    counter=0
    while while_func(*while_func_args):
        body_func(*body_func_args)
        waiting(2)
        if exit_func(*exit_func_args):
            break
        counter+=1
        if counter>3:
            raise TimeoutException
    waiting()
def journal_open():
    Log.info('----------journal_open-------------')
    counter=0
    while True:
        click_xpath("//*[contains(@class,'x6-menu-item-icon-default x6-menu-item-icon direction16-2017')]", wait=5,crit=False)
        if click_xpath("//*[contains(@class,'x6-menu-item-text')][contains(text(),'Отказ')]", wait=5,crit=False):
            break
        counter+=1
        if counter>10:
            raise TimeoutException
    waiting()
def journal_setup(date_from, date_to):
    Log.info(f'----------journal_setup------------ {date_from +" — " + date_to}')
    try:
        xpath="//div[contains(@class,'dateRangeField') and contains(.//*,'Диапазон дат поступления')]//input"
        string=date_from +" - " + date_to
        element = click_xpath(xpath)
        script = """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('change'));
        """
        DriverManager.get_driver().execute_script(script, element, string)
        time.sleep(0.3)
        webdriver.ActionChains(DriverManager.get_driver()).send_keys(Keys.ENTER).perform()
        if hover_n_click_text("Применить", wait=30):
            return True
    except Exception as e:
        Log.error(f"Ошибка при настройке журнала: {e}")
    return False 
def type_n_select_from_list(text_to_click, text_to_type, text_to_select):
    counter=0
    while True:
        hover_n_click_text(text_to_click)
        waiting(2)
        webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys(text_to_type).perform()
        waiting(2)
        if click_xpath("//li[contains(@class, 'x6-boundlist-item')][contains(text(),'"+text_to_select+"')]",wait=5,crit=False):
            break
        counter+=1
        if counter>3:
            raise TimeoutException
def check_for_forbidden_ds():
    Log.info('check_for_forbidden_ds')
    try:
        current_ds=get_element_value("//*[contains(text(),'Основной диагноз:')]/../../..//input[@type='text']")
        Log.info(f'current_ds = {current_ds}')
        if any(current_ds.lower().startswith(forbidden_code.lower()) for forbidden_code in forbidden_ds):
            Log.info(f"Запретный диагноз найден {current_ds} меняем на J06.9!")
            return True
    except Exception as e:
        Log.warning(f'check_for_forbidden_ds failed: {e}')
    return False
def sign_windows_clicks():
    Log.info('----------sign_windows_clicks------------')
    waiting()
    click_text('Подписать')
    waiting()
    click_xpath("//a[contains(@class,'x6-btn x6-unselectable x6-box-item x6-toolbar-item x6-btn-default-small') and not(contains(@aria-hidden, 'true'))]//*[contains(text(),'Продолжить')]", wait=4, crit=False)
    click_text('Нет', wait=2, crit=False, contains=False)
    click_text('OK', wait=2, crit=False)
    click_text('Понятно', wait=2, crit=False)
    click_xpath("//*[contains(text(),'Подписание данных ЭП') and contains(@id,'header-title')]/../../../../..//*[contains(@class,'x6-tool-close')]", wait=2, crit=False)
    click_text('Понятно', wait=2, crit=False)
    click_xpath("//*[@class='x6-tool-tool-el x6-tool-img x6-tool-close ']", wait=2, crit=False)
    waiting()
    # Подписание данных ЭП
def create_new_tap():
    Log.info('----------create_new_tap------------')
    need_tap_counter=0
    while True:
        click_xpath("//*[tr[td//text()[contains(., 'Нужен ТАП')]]]", wait=10, crit=False)
        if click_text('Создать ТАП', wait=10, crit=False):
            waiting()
            if click_text("Данные о завершении случая",wait=5,crit=False):
                Log.info("Случай завершён! Опять глючит! перезапускаю")
                waiting()
                click_xpath("//*[contains(@class,'x6-btn-icon-el x6-btn-icon-el-default-small emk16-2017')]/../../..//*[contains(@class,'taskbar-close-btn')]")
                waiting()
                continue
            break
        need_tap_counter+=1
        Log.info(f"не получилось, повторяю... {need_tap_counter}")
        if need_tap_counter>=2:
            raise TimeoutException
    waiting(2)
    while click_text("Данные о завершении случая",wait=5,crit=False):
        need_tap_counter=0
        while True:
            click_xpath("//*[tr[td//text()[contains(., 'Нужен ТАП')]]]", wait=10, crit=False)
            if click_text('Создать ТАП', wait=10, crit=False):
                break
            need_tap_counter+=1
            Log.info(f"не получилось, повторяю...{need_tap_counter}")
            if need_tap_counter>=2:
                raise TimeoutException
        waiting(2)
    click_xpath("//*[contains(@class,'x6-btn-inner')][contains(text(),'Да')]",wait=10, crit=False)
    waiting(2)
    click_xpath("//*[text()='OK']",wait=1, crit=False)
    waiting(2)
    click_xpath("//*[text()='Понятно']",wait=1, crit=False)
    waiting(2)
def fill_new_tap(sign=True):
    Log.info('----------fill_new_tap------------')
    if click_text("Анкетирование пациента с подозрением на COVID-19",wait=5, crit=False):
        click_xpath("//*[contains(text(),'Анкетирование пациента с подозрением на COVID-19')]/../../../../../..//*[contains(text(),'тмена')]")
    click_xpath("//*[text()='Понятно']",wait=1, crit=False)
    waiting()
    fill_invalid_fields()
    Log.info('Проверяю кто врач...')
    if 'ПЛЕНКИН АНТОН АНДРЕЕВИЧ' in get_element_value("//*[contains(text(),'Врач:')]/../../..//input[@type='text'and @aria-disabled='false']"):
        Log.info('Врач - Пленкин')
        is_plenkin=True
    else:
        Log.info('Врач - не пленкин')
        is_plenkin=False
        click_with_counter(
            click_xpath, ("//*[contains(text(),'Врач:')]/../../..//input[@type='text'and @aria-disabled='false']", 1, False ), 
            webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('ПЛЕНКИН').perform, (), 
            click_xpath, ("//*[contains(@class,'MedStaffFactCombo')]//*[contains(text(),'ПЛЕНКИН')]", 1, False) )
            # click_xpath, ("//li[contains(@class,'x6-boundlist-item')][contains(text(),'ПЛЕНКИН')]", 1, False) )

        # x6-boundlist-item MedStaffFactCombo x6-boundlist-selected
        Log.info("Теперь - Пленкин, но is_plenkin=False")
    Log.info('----------trying to close and sign ------------')
    click_class('x6-btn-icon-el x6-btn-icon-el-default-toolbar-small panicon-flag ')
    waiting()
    if click_text('Документы, требующие подписания',wait=10,crit=False):
        if is_plenkin:
            click_text('Подписать мои документы',wait=10,crit=False)
            sign_windows_clicks()
            Log.info('----------closing again------------')
            click_class('x6-btn-icon-el x6-btn-icon-el-default-toolbar-small panicon-flag ')
        else:
            Log.info('Not Plenkin - skipping signing osmotr')
            click_text('Завершить случай',wait=10,crit=False)
    hover_n_click_text('Результат обращения:')
    counter=0
    while not click_text('Лечение завершено',wait=1,crit=False):
        hover_n_click_text('Результат обращения:')
        counter+=1
        if counter>3:
            raise TimeoutException
    hover_n_click_text('Исход:')
    waiting(2)
    webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Без перемен').perform()
    waiting(2)
    click_text('Завершить случай лечения')
    waiting(2)
    if click_text('В ТАП присутствует диагноз КВИ и исход. Сохранение возможно после добавления специфики КВИ. Добавить специфику КВИ?',wait=1,crit=False):
        click_text('Продолжить')
        waiting()
        if click_text('Найдена открытая специфика',wait=1,crit=False):
            click_text('Закрыть')
            click_xpath("//*[text()='Дата исхода:']")
            waiting(2)
            click_xpath("//*[text()='Дата исхода:']/../../..//*[contains(@id,'picker')]")
            waiting(2)
            click_text('Сегодня')
            click_text('Закрыть специфику')
            waiting()
        scroll_element_to_bottom("//*[@class='x6-panel-body x6-panel-body-default x6-panel-body-default x6-scroller x6-docked-noborder-top x6-docked-noborder-right x6-docked-noborder-bottom x6-docked-noborder-left']")
        waiting(2)
        click_xpath("(//*[text()='Дата исхода:'])[2]")
        waiting(2)
        click_xpath("(//*[text()='Дата исхода:'])[2]/../../..//*[contains(@id,'picker')]")
        waiting(2)
        click_text('Сегодня')
        waiting(2)
        click_text('Сохранить')
        waiting()
        if click_text('OK', wait=120,crit=False):
                click_xpath("//*[@class='x6-tool-tool-el x6-tool-img x6-tool-close ']")
        else:
            click_xpath("//span[text()='СПЕЦИФИКА. КВИ']/../../..//*[@class='taskbar-close-btn']",wait=1,crit=False)
        waiting(2)
        waiting()
        click_text('Завершить случай лечения')
    waiting()
    if is_plenkin:
        if not click_xpath("//*[contains(text(),'Случай амбулаторного лечения')]/../../../../../../..//*[contains(@data-qtip,'Подписать документ')]",wait=10,crit=False):
            waiting(2)
            click_xpath("//*[contains(text(),'Случай амбулаторного лечения')]/../../../../../../..//*[contains(@data-qtip,'Документ не актуален')]") 
            waiting(2)
            click_xpath("//*[contains(@class,'emd-menu')]//*[text()='Подписать']")
            waiting(2)
        sign_windows_clicks()
    else:
        Log.info('Not Plenkin - skipping signing case')
    click_xpath("//*[contains(@class,'x6-btn-icon-el x6-btn-icon-el-default-small emk16-2017')]/../../..//*[contains(@class,'taskbar-close-btn')]")
    waiting(2)
def fill_invalid_fields():
    Log.info('----------fill_invalid_fields------------')
    if check_for_forbidden_ds():
        type_n_select_from_list(text_to_click='Основной диагноз:', text_to_type='о069', text_to_select=' Острая инфекция верхних дыхательных путей неуточненная')
        waiting()
    click_with_counter(
        click_xpath, ("//*[contains(text(),'Вид обращения:')]/../../..//*[contains(@class,'x6-form-text-wrap-invalid')]", 1, False ), 
        webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Другие обстоятельства (С профилактическими и иными целями)').perform, (), 
        click_xpath, ("//li[contains(@class,'x6-boundlist-item')][contains(text(),'Другие обстоятельства (С профилактическими и иными целями)')]", 1, False) )
    click_with_counter(
        click_xpath, ("//*[contains(text(),'Место:')]/../../..//*[contains(@class,'x6-form-text-wrap-invalid')]", 1, False ), 
        webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Поликлиника').perform, (), 
        click_xpath, ("//li[contains(@class,'x6-boundlist-item')][contains(text(),'Поликлиника')]", 1, False) )
    try:
        click_with_counter(
            click_xpath, ("//*[contains(text(),'Цель посещения:')]/../../..//*[contains(@class,'x6-form-text-wrap-invalid')]", 1, False ), 
            webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Другое').perform, (), 
            click_xpath, ("//li[contains(@class,'x6-boundlist-item')][contains(text(),'Другое')]", 1, False) )
    except TimeoutException as e:
        click_with_counter(
            click_xpath, ("//*[contains(text(),'Цель посещения:')]/../../..//*[contains(@class,'x6-form-text-wrap-invalid')]", 1, False ), 
            webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Лечебно-диагностическая').perform, (), 
            click_xpath, ("//li[contains(@class,'x6-boundlist-item')][contains(text(),'Лечебно-диагностическая')]", 1, False) )
    if 'Удовлетворительное' not in get_element_value("//*[contains(text(),'Состояние пациента')]/../../..//input[@type='text']"):
        click_with_counter(
            click_xpath, ("//*[contains(text(),'Состояние пациента')]/../../..//div[contains(@class,'x6-form-trigger x6-form-trigger-default x6-form-arrow-trigger x6-form-arrow-trigger-default ')]", 5, False), 
            webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Удовлетворительное').perform, (), 
            click_xpath, ("//li[contains(@class,'x6-boundlist-item')][contains(text(),'Удовлетворительное')]", 5, False) )
        click_xpath("//*[text()='Понятно']",wait=5, crit=False)
        waiting()
    if 'B01.014.001.222' not in get_element_value("//*[contains(text(),'Код посещения:')]/../../..//input[@type='text']"):
        click_with_counter(
            click_xpath, ("//*[contains(text(),'Код посещения:')]/../../..//div[contains(@class,'x6-form-trigger x6-form-trigger-default x6-form-arrow-trigger x6-form-arrow-trigger-default ')]", 5, False), 
            webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('B01.014.001.222').perform, (), 
            click_xpath, ("//nobr[text()='B01.014.001.222']", 5, False) )
        click_xpath("//*[text()='Понятно']",wait=5, crit=False)
        waiting()
    Log.debug('Проверяю не стоит ли Подозрение на ЗНО')
    if 'Да' in get_element_value("//*[contains(text(),'Подозрение на ЗНО:')]/../../..//input[@type='text']"):
        click_with_counter(
            click_xpath, ("//*[contains(text(),'Подозрение на ЗНО:')]/../../..//div[contains(@class,'x6-form-trigger x6-form-trigger-default x6-form-arrow-trigger x6-form-arrow-trigger-default ')]", 5, False), 
            webdriver.ActionChains(DriverManager.get_driver()).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.DELETE).send_keys('Нет').perform, (), 
            click_xpath, ("//li[text()='Нет']", 5, False))
        click_text('Да')
def check_last_tap():
    Log.info('----------Check last tap------------')
    if not click_text("Нужен ТАП", wait=10, crit=False):
        return
    waiting()
    taps=DriverManager.get_driver().find_elements(By.XPATH,"//*[contains(text(),'ТАП №')]")
    last_tap_num=0
    last_tap_text="no tap"
    for tap in taps:
        i = int(tap.text[5:])
        if last_tap_num<i:
                last_tap_num=i
                last_tap_text=tap.text
    if last_tap_num==0:
        Log.info("Нет ТАПов")
        return
    Log.info(f"Последний ТАП: {last_tap_text}")
    while True:
        click_xpath("//*[tr[td//text()[contains(., '"+last_tap_text+"')]]]", wait=10, crit=False)
        if click_text("Открыть ТАП", wait=10, crit=False):
            break
        Log.info("не получилось, повторяю...")
    waiting()
    click_xpath("//*[text()='Понятно']",wait=1, crit=False)
    if click_text("Данные о завершении случая",wait=5,crit=False):
        Log.info("Случай завершён! Ура!")
        click_xpath("//*[contains(@class,'x6-btn-icon-el x6-btn-icon-el-default-small emk16-2017')]/../../..//*[contains(@class,'taskbar-close-btn')]")
        return
    Log.info("Ага! Попался не закрытый!")
    fill_new_tap()
def hot_restart(date_from, date_to):
    while True:
        Log.info('----------hot_restart----------')
        DriverManager.get_driver().refresh()
        waiting()
        if click_xpath("//*[@id='promed-password']",wait=1,crit=False):
            Log.info("Обнаружена страница входа, перелогинюсь")
            login()
            # select_arm()
        journal_open()
        if journal_setup(date_from=date_from, date_to=date_to):
            break
    waiting()
def take_screenshot():
    """Take screenshot and return as bytes"""
    try:
        driver = DriverManager.get_driver()
        return driver.get_screenshot_as_png()
    except Exception as e:
        Log.warning(f"Failed to take screenshot: {str(e)}")
        return None
def main(date_from, date_to, max_errors=3, max_attempts=50):
    need_to_check_last_tap = True
    attempt = 0
    consecutive_errors = 0
    while True:
        try:
            Log.info(f'-------------------------main loop starting ({date_from} - {date_to}) try {consecutive_errors+1} from {max_errors}---------------------------')
            print(f"---set-current-day---{date_from}---")
            if need_to_check_last_tap:
                check_last_tap()
                need_to_check_last_tap = False
                hot_restart(date_from=date_from, date_to=date_to)
            need_to_check_last_tap = True
            create_new_tap()
            waiting()
            fill_new_tap(sign=True)
            need_to_check_last_tap = False
            
            attempt += 1
            hot_restart(date_from=date_from, date_to=date_to)
            consecutive_errors = 0
            if attempt > max_attempts:
                return
        except (ClickError, TimeoutException) as e:
            consecutive_errors += 1
            screenshot = take_screenshot()
            Log.warning(f"consecutive_errors = {consecutive_errors}. Exception type: {type(e).__name__}. Exception details: {str(e)}")
            if consecutive_errors >= max_errors:
                error_msg = f"Critical: {consecutive_errors} consecutive errors occurred. Last error: {type(e).__name__}: {str(e)}"
                send_telegram_alert(error_msg, screenshot)
                return
            hot_restart(date_from=date_from, date_to=date_to)
            if attempt > max_attempts:
                return
def watchdog():
    while True:
        time.sleep(60)
        try:
            if not DriverManager.get_driver().current_url:
                raise Exception("Browser unresponsive")
        except:
            Log.error("Watchdog detected hang - restarting")
            DriverManager.start_driver(restart=True)

def run_bot(num_instance, start_date, counter=1):
    try:
        Log.info(f"*** Instance {num_instance} started. start_date={start_date}, counter={counter}***")
        Log.info(f"Starting driver for instance {num_instance}...")
        DriverManager.start_driver(url=url+'?c=portal&m=udp', restart=False, num_instance=num_instance)
        Log.info(f"Driver started for instance {num_instance}.")
        threading.Thread(target=watchdog, daemon=True).start()
        current_date_from = start_date
        current_date_to = start_date
        count = 0
        login()
        # select_arm()
        journal_open()
        journal_setup(date_from=start_date, date_to=start_date)
        while count < counter:
            Log.info(f"Loop {count} from {counter}")
            try:
                main(date_from=current_date_from, date_to=current_date_to, max_errors=3, max_attempts=50)
            except Exception as e:
                Log.info(f"Loop {count} from {counter} exception: {e}.")
            Log.info(f"Loop {count} from {counter} exited.")
            current_date_from = add_one_day(current_date_from)
            current_date_to = add_one_day(current_date_to)
            hot_restart(date_from=current_date_from, date_to=current_date_to)
            count += 1
        Log.info(f"Loop {count} from {counter}. Exiting. Good bye!")   
        DriverManager.get_driver().quit()
    except Exception as e:
        Log.error(f"Ошибка в экземпляре {num_instance}: {str(e)}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 4:
        run_bot(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
    else:
        print("Usage: python script.py <instance_num> <start_date> <days>")