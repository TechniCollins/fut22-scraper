from django.core.management.base import BaseCommand

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import time
import os

from scraper.models import BusinessDetail, VerificationCode, MatchCount

from datetime import datetime, timedelta

from django.core.mail import EmailMessage

# For copyting temp files
import shutil
import getpass


class Command(BaseCommand):
    DELAY = 10 # max time when waiting for element

    def createChromeProfile(self, user_id):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )
        chrome_profile = driver.capabilities.get("chrome").get("userDataDir")

        # By default selenium saves Chrome profiles in /tmp
        # These files are deleted on shutdown, so copy them to
        # a "permanent" location
        os_user = getpass.getuser()
        profile_dir = f"/home/{os_user}/fut22scraper-chromeprofiles/{user_id}"
        try:
            shutil.copytree(chrome_profile, profile_dir)
        except Exception as e:
            print(e)
            # Some file like SingletonCookie can't be copied. Dk what the problem is, so ignore
            # them for now

        print(profile_dir)

        # Save chrome profile
        b = BusinessDetail.objects.get(user__id=user_id)
        b.chrome_profile = profile_dir
        b.save()

        return profile_dir


    def setChromeBrowser(self, chrome_profile):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        if os.path.isdir(chrome_profile):
            chrome_options.add_argument(f"user-data-dir={chrome_profile}") # Each user will have their own profile

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        return driver


    def waitForElementByXpath(self, driver, xpath):
        try:
            elem = WebDriverWait(
                driver, self.DELAY
            ).until(
                EC.element_to_be_clickable(
                    (By.XPATH, xpath)
                )
            )
        except TimeoutException:
            elem = None

        return elem


    def checkIfElementExistsById(self, driver, element_id):
        try:
            elem = driver.find_element(By.ID, element_id)
        except NoSuchElementException:
            elem = None

        return elem


    def checkIfElementExistsByXpath(self, driver, xpath):
        try:
            elem = WebDriverWait(
                driver, self.DELAY
            ).until(
                EC.presence_of_element_located(
                    (By.XPATH, xpath)
                )
            )
        except TimeoutException:
            elem = None

        return elem


    def loginToEA(self, driver, b):
        login_button = self.waitForElementByXpath(driver, '/html/body/main/div/div/div/button[1]')

        # if None is returned it may mean last login is still valid and FUT is loading or has
        # already been loaded.
        if login_button:
            # Click on login button
            login_button.click()

            # Wait for login form to load then enter credentials

            email_field = WebDriverWait(
                driver, self.DELAY
            ).until(
                EC.presence_of_element_located(
                    (By.NAME, "email")
                )
            )

            password_field = driver.find_element(By.NAME, "password")

            email_field.send_keys(b.ea_email) # Get from DB per user
            password_field.send_keys(b.ea_password) # Get from DB per user
            password_field.submit()

            time.sleep(3)

            # Check if there's an email verification button
            verification_button = self.checkIfElementExistsById(driver, "btnSendCode")

            # if button exists, go through verification process
            if verification_button:
                verification_button.click()

                # For now, we will require a verification code record to be added to the database.
                # The admin will have 2 minutes to update the records
                # Since verification will be needed only once, this is a viable solution
                time.sleep(120) # Give the admin time to update the database from django admin

                otp = VerificationCode.objects.filter(user=b.user).order_by("-id")[0] # Get latest entry for specified user

                # input whatever info we retrieved from the user
                otp_field = WebDriverWait(
                    driver, self.DELAY
                ).until(
                    EC.presence_of_element_located(
                        (By.NAME, "oneTimeCode")
                    )
                )
                otp_field.send_keys(otp.code)
                otp_field.submit()

        return


    def scrapeFUT(self, b):
        chrome_profile = b.chrome_profile

        if not chrome_profile:
            print("No chrome profile found. Creating")
            chrome_profile = self.createChromeProfile(b.user.id)

        driver = self.setChromeBrowser(chrome_profile)

        # Go to fut22 web app
        driver.get("https://www.ea.com/fifa/ultimate-team/web-app/")

        # Check if login is required
        login = self.checkIfElementExistsByXpath(driver, '/html/body/main/div[@id="Login"]')

        # Log in
        if login:
            print("Logging in to FUT22")
            self.loginToEA(driver, b)

        try:
            # After settings button is available, click on it
            settings_button = WebDriverWait(
                driver, 30
            ).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '/html/body/main/section/nav/button[9]')
                )
            )
            settings_button.click()

            playtime_button = WebDriverWait(
                driver, self.DELAY
            ).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '/html/body/main/section/section/div[2]/div/div/div[2]/div[1]/button[@class="more"]')
                )
            )
            playtime_button.click()

            time.sleep(3)

            matches = self.checkIfElementExistsByXpath(driver, '/html/body/main/section/section/div[2]/div/div[2]/div[4]/div[@class="tileContent"]/div/div/div[1]/span[@class="value"]')

            if not matches:
                print("Matches data not found.")
                return

            total_week_matches = int(matches.text.split("/")[0])

            # Close Browser
            driver.close()

            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            # Find the latest match count record for the previous day
            last_match = MatchCount.objects.filter(
                user=b.user,
                time__contains=yesterday
            ).order_by("-time").first()

            message = f"{b.business_name}\nTotal Games this week: {total_week_matches}"

            # If there's no data yet
            if not last_match.count:
                message = f"{message}\nTotal matches today: No data"

            # If matches have reset
            if total_week_matches < last_match.count:
                message = f"{message}\nTotal matches today: {last_match.count}"
            else:
                message = f"{message}\nTotal matches today: {total_week_matches - last_match.count}"

            # Save today's data
            MatchCount.objects.create(
                user=b.user,
                count=total_week_matches
            )

            # Send results via email
            mail = EmailMessage(
                subject=f"Fifa 22 games played - {datetime.today()}",
                body=message,
                to=[b.user.email, "collins@softlever.com"]
            )

            mail.send()

        except TimeoutException:
            print("Timed out before loading web app")

        return


    def handle(self, *args, **options):
        # Get all businesses to run scraper for
        business_details = BusinessDetail.objects.all().prefetch_related()

        for b in business_details:
            self.scrapeFUT(b)

        return
