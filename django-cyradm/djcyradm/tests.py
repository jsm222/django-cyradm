from os.path import isfile
from time import sleep
import rules
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.test import Client
from django.test.utils import override_settings
from django.test import tag
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
import djcyradm.overrides
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import LiveServerTestCase
from django.test import TransactionTestCase
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.select import Select
from djcyradm.models import MailUsers, Domains, VirtualDelivery


@override_settings(DJCYRADM_SYNCIMAP=False, LANGUAGE_CODE="en-US", LANGUAGES=[('en', 'English')])
class MySeleniumTests(LiveServerTestCase):
    fixtures = ["djcyradm_test001"]

    @classmethod
    def setUpClass(cls):
        super(MySeleniumTests, cls).setUpClass()
        if isfile("/usr/local/bin/firefox"):
            binary = FirefoxBinary("/usr/local/bin/firefox")
        else:
            binary = FirefoxBinary("/usr/bin/firefox")
        cls.selenium = WebDriver(firefox_binary=binary)
        cls.selenium.implicitly_wait(40)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(MySeleniumTests, cls).tearDownClass()

    def make_alias_assert_noperm(self):
        WebDriverWait(self.selenium, 20).until(
            lambda driver: self.selenium.find_element_by_xpath("//ul[@class='messages']/li"))
        self.assertEquals(self.selenium.find_element_by_xpath("//ul[@class='messages']/li").text,
                          "You are not allowed to add (any further) aliases")

    def make_alias_assert_error(self, error="", idstr="id_alias", sel="input"):
        WebDriverWait(self.selenium, 20).until(
            lambda driver: self.selenium.find_element_by_xpath(
                "//" + sel + "[@id='" + idstr + "']/..//div[@class='help-block'][1]"))
        # self.assertEquals(
        #   self.selenium.find_element_by_xpath("//"+sel+"[@id='"+idstr+"']/..//div[@class='help-block']").text,
        #  error)
        sleep(1)
        self.assertEquals(self.selenium.find_element_by_xpath(
            "//" + sel + "[@id='" + idstr + "']/..//div[@class='help-block'][1]").text, error)

    def make_alias_assert_success(self, alias, dest, alias_domain):
        sleep(1)
        try:

            self.selenium.find_element_by_link_text("Aliases").click()
            WebDriverWait(self.selenium, 20).until(
                lambda driver: self.selenium.find_element_by_xpath(
                    "//li[contains(@class,'open')]/ul/li//a[@href='/djcyradm/aliases/']"))

            self.selenium.find_element_by_xpath(
                "//li[contains(@class,'open')]/ul/li//a[@href='/djcyradm/aliases/']").click()

            WebDriverWait(self.selenium, 20).until(
                lambda driver: self.selenium.find_element_by_xpath("//td[@class='dest']"))
            sleep(1)
            for x in self.selenium.find_elements_by_xpath("//td[@class='dest']"):
                self.assertEquals(x.text, dest)
        except NoSuchElementException as e:
            raise e
        self.assertQuerysetEqual(VirtualDelivery.objects.filter(full_dest="myuser@example.com"),
                                 map(repr, VirtualDelivery.objects.filter(
                                     dest=MailUsers.objects.get(username="myuser@example.com"))),
                                 ordered=False)

    def do_t_login(self):

        self.assertQuerysetEqual(MailUsers.objects.get(username="cyrus").groups.all(),
                                 map(repr, Group.objects.filter(name="admins").all()))
        self.assertTrue(MailUsers.objects.get(username="cyrus").has_perm("djcyradm.list_domains"))
        self.selenium.get('%s%s' % (self.live_server_url, '/djcyradm/login/'))

        self.selenium.find_element_by_id("id_username").clear()
        self.selenium.find_element_by_id("id_username").send_keys("myuser@example.com")
        self.selenium.find_element_by_id("id_password").clear()
        self.selenium.find_element_by_id("id_password").send_keys("cyrus")
        self.selenium.find_element_by_css_selector("button.btn.btn-primary").click()
        sleep(1)

    def test_login(self):
        self.do_t_login()
        WebDriverWait(self.selenium, 20).until(
            lambda driver: self.selenium.find_element_by_xpath("//div[@id='bar1']//li/a[@href='/djcyradm/aliases/']"))
        self.assertEquals(
            self.selenium.find_element_by_xpath("//div[@id='bar1']//li/a[@href='/djcyradm/aliases/']").get_attribute(
                "class"), '')
        # login

    def test_make_aliases(self):
        self.do_t_login()
        self.make_alias(alias="test@example.com", dest="myuser@example.com", alias_domain="example.com")
        self.make_alias_assert_success(alias="test", dest="myuser@example.com", alias_domain="example.com")

        self.make_alias(alias="test@example.com", dest="myuser@example.com", alias_domain="example.com")
        self.make_alias_assert_error(error="Alias already exists")

        self.selenium.get('%s%s' % (self.live_server_url, '/djcyradm/mail-users'))
        self.make_alias(alias="test@tester1.dk", dest="myuser@example.com", alias_domain="example.com")
        self.make_alias_assert_error(error="tester1.dk is not the alias domain example.com")

        self.selenium.get('%s%s' % (self.live_server_url, '/djcyradm/mail-users'))
        self.make_alias(alias="myuser", dest="myuser@example.com", alias_domain="example.com")
        self.make_alias_assert_error(error="A user has the wanted alias as username")

        self.selenium.get('%s%s' % (self.live_server_url, '/djcyradm/mail-users'))
        self.make_alias(alias="test1@example.com", dest="myuser@example.com", alias_domain="example.com")
        sleep(1)
        self.make_alias_assert_success(alias="test1", dest="myuser@example.com", alias_domain="example.com")

        self.assertEquals(Domains.objects.get(domain_name="example.com").max_aliases_per_account, 2)
        self.assertEqual(VirtualDelivery.objects.filter(full_dest="myuser@example.com").count(), 2)

        self.selenium.get('%s%s' % (self.live_server_url, '/djcyradm/mail-users'))
        WebDriverWait(self.selenium, 20).until(
            lambda driver: self.selenium.find_element_by_link_text("Aliases"))
        self.make_alias(alias="test2@example.com", dest="myuser@example.com", alias_domain="example.com")
        self.make_alias_assert_error(error="No more aliases for this destination", idstr="id_dest", sel="select")

        self.assertQuerysetEqual(VirtualDelivery.objects.filter(full_dest="myuser@example.com"),
                                 map(repr, VirtualDelivery.objects.filter(dest=MailUsers.objects.get(
                                     username="myuser@example.com"))),
                                 ordered=False)

    def make_alias(self, alias, alias_domain, dest):
        self.selenium.find_element_by_link_text("Aliases").click()
        WebDriverWait(self.selenium, 20).until(
            lambda driver: self.selenium.find_element_by_xpath(
                "//li[contains(@class,'open')]/ul/li//a[@href='/djcyradm/aliases/add/']"))
        sleep(1)
        self.selenium.find_element_by_xpath(
            "//li[contains(@class,'open')]/ul/li//a[@href='/djcyradm/aliases/add/']").click()
        WebDriverWait(self.selenium, 20).until(
            lambda driver: self.selenium.find_element_by_id("id_alias"))

        sleep(1)
        self.selenium.find_element_by_id("id_alias").clear()
        self.selenium.find_element_by_id("id_alias").send_keys(alias)
        Select(self.selenium.find_element_by_id("id_alias_domain")).select_by_visible_text(alias_domain)
        Select(self.selenium.find_element_by_id("id_dest")).select_by_visible_text(dest)
        self.selenium.find_element_by_css_selector("button.btn.btn-primary").click()

    def prep_add_ccount(self):

        if not MailUsers.objects.get_by_natural_key("myuser@example.com").groups.filter(
                name="admins").exists() and not MailUsers.objects.get_by_natural_key(
                "myuser@example.com").groups.filter(name="domainadmins").exists():
            self.selenium.get(self.live_server_url + "/djcyradm/mail-users/add/")
            self.assertEquals(self.selenium.find_element_by_xpath("/html/body/ul/li").text,
                              "You are not allowed to add accounts")
            return False
        else:
            self.selenium.get(self.live_server_url + "/djcyradm/mail-users")
            self.selenium.find_element_by_link_text("Accounts").click()
            self.selenium.find_element_by_link_text("Add").click()
        return True

    def test_addaccount_max_quota_to_big(self):
        self.do_t_login()
        if self.prep_add_ccount():
            WebDriverWait(self.selenium, 20).until(
                lambda driver: self.selenium.find_element_by_id(
                    "id_username"))
            sleep(1)
            self.selenium.find_element_by_id("id_username").clear()
            self.selenium.find_element_by_id("id_username").send_keys("test")
            Select(self.selenium.find_element_by_id("id_domain")).select_by_visible_text("example.com")
            self.selenium.find_element_by_id("id_quota").clear()
            self.selenium.find_element_by_id("id_quota").send_keys(
                str(Domains.objects.filter(domain_name="example.com").first().max_quota_per_account + 1))
            self.selenium.find_element_by_id("id_max_aliases").clear()
            self.selenium.find_element_by_id("id_max_aliases").send_keys("1")
            self.selenium.find_element_by_css_selector("button.btn.btn-primary").click()
            self.make_alias_assert_error(idstr="id_quota", error="The max quota for domain example.com is " + str(
                Domains.objects.filter(domain_name="example.com").first().max_quota_per_account))
            return

    def test_add_account_max_aliases_to_big(self):
        self.do_t_login()
        if self.prep_add_ccount():
            WebDriverWait(self.selenium, 20).until(
                lambda driver: self.selenium.find_element_by_id(
                    "id_username"))
            driver = self.selenium
            sleep(1)
            driver.find_element_by_id("id_username").clear()
            driver.find_element_by_id("id_username").send_keys("test")
            Select(driver.find_element_by_id("id_domain")).select_by_visible_text("example.com")
            driver.find_element_by_id("id_quota").clear()
            driver.find_element_by_id("id_quota").send_keys(
                str(Domains.objects.filter(domain_name="example.com").first().max_quota_per_account))
            driver.find_element_by_id("id_max_aliases").clear()
            driver.find_element_by_id("id_max_aliases").send_keys(
                str(Domains.objects.filter(domain_name="example.com").first().max_aliases_per_account + 1))
            driver.find_element_by_css_selector("button.btn.btn-primary").click()
            self.make_alias_assert_error(idstr="id_max_aliases",
                                         error="The max number of aliases per account for domain example.com is " + str(
                                             Domains.objects.filter(
                                                 domain_name="example.com").first().max_aliases_per_account))
            return

    def test_addaccount_alias_and_quota_to_big(self):
        self.do_t_login()
        driver = self.selenium
        if self.prep_add_ccount():
            WebDriverWait(self.selenium, 20).until(
                lambda driver: self.selenium.find_element_by_id(
                    "id_username"))

            sleep(1)
            driver.find_element_by_id("id_username").clear()
            driver.find_element_by_id("id_username").send_keys("test")
            Select(driver.find_element_by_id("id_domain")).select_by_visible_text("example.com")
            driver.find_element_by_id("id_quota").clear()
            driver.find_element_by_id("id_quota").send_keys(
                str(Domains.objects.filter(domain_name="example.com").first().max_quota_per_account + 1))
            driver.find_element_by_id("id_max_aliases").clear()
            driver.find_element_by_id("id_max_aliases").send_keys(
                str(Domains.objects.filter(domain_name="example.com").first().max_aliases_per_account + 1))
            driver.find_element_by_css_selector("button.btn.btn-primary").click()
            sleep(2)
            self.make_alias_assert_error(idstr="id_max_aliases",
                                         error="The max number of aliases per account for domain example.com is " + str(
                                             Domains.objects.filter(
                                                 domain_name="example.com").first().max_aliases_per_account))
            self.make_alias_assert_error(idstr="id_quota", error="The max quota for domain example.com is " + str(
                Domains.objects.filter(domain_name="example.com").first().max_quota_per_account))


@tag("Simple")
@override_settings(DJCYRADM_SYNCIMAP=False, LANGUAGE_CODE="en", LANGUAGES=[('en', 'English')])
class SimpleTest(TransactionTestCase):
    fixtures = ["djcyradm_test001"]

    def setUp(self):
        self.client = Client()

    def test_login(self):
        # Issue a GET request.

        self.assertTrue(self.client.login(username="myuser@example.com", password="cyrus"))
        user = MailUsers.objects.get(is_active=True, is_main_cyrus_admin=False, username="myuser@example.com",
                                     domain=Domains.objects.get(domain_name="example.com"))
        self.assertEquals(user.domain.domain_name, "example.com")
        self.assertIsNotNone(user.domain)
        self.assertTrue(user.check_password("cyrus"))

    def test_make_alias(self):
        domain = Domains.objects.get(domain_name="example.com")
        self.assertEquals(domain.domain_name, "example.com")
        user = MailUsers.objects.get(is_active=True, is_main_cyrus_admin=False, username="myuser@example.com",
                                     domain=domain)
        self.assertEquals(user.domain, domain)
        self.assertTrue(user.check_password("cyrus"))
        self.client.post("/djcyradm/login/", {'username': "myuser@example.com", "password": "cyrus"})
        self.client.login(username="myuser@example.com", password="cyrus")
        resp = self.client.post("/djcyradm/aliases/add/",
                                {"dest": user.id, "alias_domain": domain.id,
                                 "alias": "test"})
        self.assertEquals(resp.status_code, 302)
        self.assertEquals(resp.url, "/djcyradm/aliases/")
        self.assertEquals(
            VirtualDelivery.objects.filter(full_dest="myuser@example.com", alias_domain_id=domain.id,
                                           dest__id=user.id).first().dest,
            MailUsers.objects.get(username="myuser@example.com"))

        resp = self.client.post("/djcyradm/aliases/add/",
                                {"dest": user.id, "alias_domain": domain.id,
                                 "alias": "test"})
        self.assertFormError(resp, "form", "alias", 'Alias already exists')
        domain.max_aliases_per_account = 1
        domain.save()

        self.assertEquals(user.domain, domain)
        self.assertEquals(domain.max_aliases_per_account, 1)
        domain.max_aliases_per_account = 1
        domain.save()
        self.assertEquals(user.domain, domain)
        self.assertEquals(domain.max_aliases_per_account, 1)
        user.domain.refresh_from_db()

        self.assertEquals(user.domain.max_aliases_per_account, 1)

        resp = self.client.post("/djcyradm/aliases/add/",
                                {"dest": user.id, "alias_domain": domain.id,
                                 "alias": "test1"})
        self.assertFormError(resp, 'form', 'dest', 'No more aliases for this destination')

    def test_make_account(self):

        user = MailUsers.objects.get(is_active=True, is_main_cyrus_admin=False, username="myuser@example.com"
                                     )

        self.assertTrue(user.check_password("cyrus"))
        self.client.post("/djcyradm/login/", {'username': "myuser@example.com", "password": "cyrus"})
        with self.settings(SYNCIMAP=False):

            self.client.login(username="myuser@example.com", password="cyrus")
            domain = Domains.objects.get(domain_name="example.com")
            resp = self.client.post("/djcyradm/mail-users/add/",
                                    {"username": "test", "domain": domain.id, "groups": "3", "quota": "102400",
                                     "max_aliases": domain.max_aliases_per_account})

            loggedin = MailUsers.objects.get(is_active=True, is_main_cyrus_admin=False, username="myuser@example.com")

            if loggedin.groups.filter(name="domainadmins").exists():
                user = MailUsers.objects.get(is_active=True, is_main_cyrus_admin=False, username="test@example.com")
                self.assertEquals(resp.status_code, 302)
                self.assertEquals(resp.url, "/djcyradm/mail-users/" + str(user.id) + "/password/reset/")

                self.assertEquals(user.username, "test@example.com")

                resp = self.client.post("/djcyradm/mail-users/add/",
                                        {"username": "test", "domain": 2, "groups": 3, "quota": "102400",
                                         "max_aliases": domain.max_aliases_per_account})

                self.assertFormError(resp, "form", "domain",
                                     'Select a valid choice. That choice is not one of the available choices.')

                self.assertEquals(resp.status_code, 200)
            else:
                self.assertEquals(resp.status_code, 403)


@override_settings(DJCYRADM_SYNCIMAP=False, LANGUAGE_CODE="en", LANGUAGES=[('en', 'English')])
class MySeleniumTests2(MySeleniumTests):
    fixtures = ["djcyradm_test002"]


@tag("Simple")
@override_settings(DJCYRADM_SYNCIMAP=False, LANGUAGE_CODE="en", LANGUAGES=[('en', 'English')])
class SimpleTest2(SimpleTest):
    fixtures = ["djcyradm_test002"]
