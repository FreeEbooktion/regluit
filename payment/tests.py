"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.utils import unittest
from django.conf import settings
from regluit.payment.manager import PaymentManager
from regluit.payment.models import Transaction
from regluit.core.models import Campaign, Wishlist, Work
from regluit.payment.parameters import *
from regluit.payment.paypal import *
import traceback
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import logging
import os
from decimal import Decimal as D
from regluit.utils.localdatetime import now
from datetime import timedelta

def setup_selenium():
    # Set the display window for our xvfb
    os.environ['DISPLAY'] = ':99'

def set_test_logging():
    
    # Setup debug logging to our console so we can watch
    defaultLogger = logging.getLogger('')
    defaultLogger.addHandler(logging.StreamHandler())
    defaultLogger.setLevel(logging.DEBUG)
    
    # Set the selenium logger to info
    sel = logging.getLogger("selenium")
    sel.setLevel(logging.INFO)

def loginSandbox(selenium):
    
    print "LOGIN SANDBOX"
    
    try:
        selenium.get('https://developer.paypal.com/')
        login_email = WebDriverWait(selenium, 10).until(lambda d : d.find_element_by_id("login_email"))
        login_email.click()
        login_email.send_keys(settings.PAYPAL_SANDBOX_LOGIN)
        
        login_password = WebDriverWait(selenium, 10).until(lambda d : d.find_element_by_id("login_password"))
        login_password.click()
        login_password.send_keys(settings.PAYPAL_SANDBOX_PASSWORD)
        
        submit_button = WebDriverWait(selenium, 10).until(lambda d : d.find_element_by_css_selector("input[class=\"formBtnOrange\"]"))
        submit_button.click()
    
    except:
        traceback.print_exc()
    
def paySandbox(test, selenium, url, authorize=False):
    
    if authorize:
        print "AUTHORIZE SANDBOX"
    else:
        print "PAY SANDBOX"
    
    try:
        # We need this sleep to make sure the JS engine is finished from the sandbox loging page
        time.sleep(20)    

        selenium.get(url)
        print "Opened URL %s" % url
   
        try:
            # Button is only visible if the login box is NOT open
            # If the login box is open, the email/pw fiels are already accessible
            login_element = WebDriverWait(selenium, 30).until(lambda d : d.find_element_by_id("loadLogin"))
            login_element.click()

            # This sleep is needed for js to slide the buyer login into view.  The elements are always in the DOM
            # so selenium can find them, but we need them in view to interact
            time.sleep(20)
        except:
            print "Ready for Login"

        email_element = WebDriverWait(selenium, 60).until(lambda d : d.find_element_by_id("login_email"))
        email_element.click()
        email_element.send_keys(settings.PAYPAL_BUYER_LOGIN)
        
        password_element = WebDriverWait(selenium, 60).until(lambda d : d.find_element_by_id("login_password"))
        password_element.click()
        password_element.send_keys(settings.PAYPAL_BUYER_PASSWORD)

        submit_button = WebDriverWait(selenium, 60).until(lambda d : d.find_element_by_id("submitLogin"))
        submit_button.click()
      
        # This sleep makes sure js has time to animate out the next page
        time.sleep(20)

        final_submit = WebDriverWait(selenium, 60).until(lambda d : d.find_element_by_id("submit.x"))
        final_submit.click()
       
        # This makes sure the processing of the final submit is complete
        time.sleep(20)

        # Don't wait too long for this, it isn't really needed.  By the time JS has gotten around to 
        # displaying this element, the redirect has usually occured       
        try:
            return_button = WebDriverWait(selenium, 10).until(lambda d : d.find_element_by_id("returnToMerchant"))
            return_button.click()
        except:
            blah = "blah"
        
    except:
        traceback.print_exc()
    
    print "Tranasction Complete"
    
class PledgeTest(TestCase):
    
    def setUp(self):
        self.verificationErrors = []
        # This is an empty array where we will store any verification errors
        # we find in our tests

        setup_selenium()
        self.selenium = webdriver.Firefox()
        set_test_logging()

    def validateRedirect(self, t, url, count):
    
        self.assertNotEqual(url, None)
        self.assertNotEqual(t, None)
        self.assertEqual(t.receiver_set.all().count(), count)
        self.assertEqual(t.receiver_set.all()[0].amount, t.amount)
        self.assertEqual(t.receiver_set.all()[0].currency, t.currency)
        # self.assertNotEqual(t.ref1Gerence, None)
        self.assertEqual(t.error, None)
        self.assertEqual(t.status, IPN_PAY_STATUS_CREATED)
        
        valid = URLValidator(verify_exists=True)
        try:
            valid(url)
        except ValidationError, e:
            print e
        
    @unittest.expectedFailure
    def test_pledge_single_receiver(self):
        
        try:
            p = PaymentManager()
    
            # Note, set this to 1-5 different receivers with absolute amounts for each
            receiver_list = [{'email':settings.PAYPAL_GLUEJAR_EMAIL, 'amount':20.00}]
            t, url = p.pledge('USD', TARGET_TYPE_NONE, receiver_list, campaign=None, list=None, user=None)
        
            self.validateRedirect(t, url, 1)
        
            loginSandbox(self.selenium)
            paySandbox(self, self.selenium, url)
            
            # sleep to make sure the transaction has time to complete
            time.sleep(10)
                    
            # by now we should have received the IPN
            # right now, for running on machine with no acess to IPN, we manually update statuses
            p.checkStatus()
            t = Transaction.objects.get(id=t.id)
            
            self.assertEqual(t.status, IPN_PAY_STATUS_COMPLETED)
            self.assertEqual(t.receiver_set.all()[0].status, IPN_TXN_STATUS_COMPLETED)
            
        except:
            traceback.print_exc()
    
    @unittest.expectedFailure    
    def test_pledge_mutiple_receiver(self):
        
        p = PaymentManager()
    
        # Note, set this to 1-5 different receivers with absolute amounts for each
        receiver_list = [{'email':settings.PAYPAL_GLUEJAR_EMAIL, 'amount':20.00}, 
                         {'email':settings.PAYPAL_TEST_RH_EMAIL, 'amount':10.00}]
        
        t, url = p.pledge('USD', TARGET_TYPE_NONE, receiver_list, campaign=None, list=None, user=None)
        
        self.validateRedirect(t, url, 2)
        
        loginSandbox(self.selenium)
        paySandbox(self, self.selenium, url)
        
        # by now we should have received the IPN
        # right now, for running on machine with no acess to IPN, we manually update statuses
        p.checkStatus()
        
        t = Transaction.objects.get(id=t.id)

        self.assertEqual(t.status, IPN_PAY_STATUS_COMPLETED)
        self.assertEqual(t.receiver_set.all()[0].status, IPN_TXN_STATUS_COMPLETED)
        self.assertEqual(t.receiver_set.all()[1].status, IPN_TXN_STATUS_COMPLETED)
    
    @unittest.expectedFailure
    def test_pledge_too_much(self):
        
        p = PaymentManager()
    
        # Note, set this to 1-5 different receivers with absolute amounts for each
        receiver_list = [{'email':settings.PAYPAL_GLUEJAR_EMAIL, 'amount':50000.00}]
        t, url = p.pledge('USD', TARGET_TYPE_NONE, receiver_list, campaign=None, list=None, user=None)
        
        self.validateRedirect(t, url, 1)

    def tearDown(self):
        self.selenium.quit()
        
class AuthorizeTest(TestCase):
    
    def setUp(self):
        self.verificationErrors = []
        # This is an empty array where we will store any verification errors
        # we find in our tests

        setup_selenium()
        self.selenium = webdriver.Firefox()
        set_test_logging()
    
    def validateRedirect(self, t, url):
    
        self.assertNotEqual(url, None)
        self.assertNotEqual(t, None)
        #self.assertNotEqual(t.reference, None)
        self.assertEqual(t.error, None)
        self.assertEqual(t.status, 'NONE')
        
        valid = URLValidator(verify_exists=True)
        try:
            valid(url)
        except ValidationError, e:
            print e
        
    def test_authorize(self):
        
        print "RUNNING TEST: test_authorize"
        
        p = PaymentManager()
    
        # Note, set this to 1-5 different receivers with absolute amounts for each
        
        t, url = p.authorize('USD', TARGET_TYPE_NONE, 100.0, campaign=None, list=None, user=None)
        
        self.validateRedirect(t, url)
        
        loginSandbox(self.selenium)
        paySandbox(self, self.selenium, url, authorize=True)
    
        # stick in a getStatus to update statuses in the absence of IPNs
        p.checkStatus()
        
        t = Transaction.objects.get(id=t.id)
        
        self.assertEqual(t.status, IPN_PAY_STATUS_ACTIVE)
        
    def tearDown(self):
        self.selenium.quit()
        
class TransactionTest(TestCase):
    def setUp(self):
        """
        """
        pass
    def testSimple(self):
        """
        create a single transaction with PAYMENT_TYPE_AUTHORIZATION / ACTIVE with a $12.34 pledge and see whether the payment
        manager can query and get the right amount.
        """
        
        w = Work()
        w.save()
        c = Campaign(target=D('1000.00'),deadline=now() + timedelta(days=180),work=w)
        c.save()
        
        t = Transaction()
        t.amount = D('12.34')
        t.type = PAYMENT_TYPE_AUTHORIZATION
        t.status = 'ACTIVE'
        t.approved = True
        t.campaign = c
        t.save()
        
        p = PaymentManager()
        results = p.query_campaign(campaign=c)
        self.assertEqual(results[0].amount, D('12.34'))
        self.assertEqual(c.left,c.target-D('12.34'))

class BasicGuiTest(TestCase):
    def setUp(self):
        self.verificationErrors = []
        # This is an empty array where we will store any verification errors
        # we find in our tests

        setup_selenium()
        self.TEST_SERVER_URL = "http://ry-dev.dyndns.org"
        self.selenium = webdriver.Firefox()
        set_test_logging()
    def testFrontPage(self):
        sel = self.selenium
        sel.get(self.TEST_SERVER_URL)
        # if we click on the learn more, does the panel expand?
        # click on a id=readon -- or the Learn More span
        sel.find_elements_by_css_selector('a#readon')[0].click()
        time.sleep(2.0)
        # the learn more panel should be displayed
        self.assertTrue(sel.find_elements_by_css_selector('div#user-block-hide')[0].is_displayed())
        # click on the panel again -- and panel should not be displayed
        sel.find_elements_by_css_selector('a#readon')[0].click()
        time.sleep(2.0)
        self.assertFalse(sel.find_elements_by_css_selector('div#user-block-hide')[0].is_displayed())
    def tearDown(self):
        self.selenium.quit()
        

def suite():

    #testcases = [PledgeTest, AuthorizeTest, TransactionTest]
    testcases = [TransactionTest]
    suites = unittest.TestSuite([unittest.TestLoader().loadTestsFromTestCase(testcase) for testcase in testcases])
    return suites    
        
       
