import csv
import os
from flask import json
import random
import re
import time
import json
# import mysql.connector
import sqlite3
from datetime import datetime
import redis
import pandas as pd
from bs4 import BeautifulSoup
from celery import Celery
import logging
import flask_login
from celery.result import AsyncResult
from flask import (Flask, jsonify, redirect, render_template, request, 
                   send_file, session, url_for, Response)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from werkzeug.security import check_password_hash, generate_password_hash
from config import *
import config
from multiprocessing import Process
import io
from flask import stream_with_context

app = Flask(__name__)

"""session configuration"""
app.config['SESSION_TYPE'] = SESSION_TYPE
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config["SECRET_KEY"] = SECRET_KEY
app.config['SESSION_REDIS'] = redis.from_url('redis://127.0.0.1:6379/0')
# app.config['SESSION_REDIS'] = redis.from_url(BROKER_URL)

sess = Session(app)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# app.config['CELERY_BROKER_URL'] = BROKER_URL
# app.config['CELERY_RESULT_BACKEND'] = BROKER_URL
#app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379'
#app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379'
celery = Celery(app.name, broker='redis://127.0.0.1:6379/0', backend='redis://127.0.0.1:6379/0')
# celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'] , backend=app.config['CELERY_RESULT_BACKEND'] )
celery.conf.update(app.config)

"""
Models
"""
@app.route("/test/data/<int:id>")
def test(id):
    scrap_data = Scrappdata.query.get(id)
    response = scrap_data.scrapped
    data = json.loads(response)
    df = pd.DataFrame.from_dict(data)
    df.to_csv('csvfile.csv', encoding='utf-8', index=True)   
    return send_file('csvfile.csv', as_attachment=True)



class ScrapData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)
    web = db.Column(db.String(150))
    keywords = db.Column(db.String(150))
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    scrapped = db.Column(db.Text())

class User(db.Model, UserMixin):
    id = db.Column('User_id', db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), unique=False, nullable=False)
    last_name = db.Column(db.String(100), unique=False, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    mobile = db.Column(db.String(12), unique=True, nullable=False)
    password = db.Column(db.String(200), unique=True, nullable=False)
    status = db.Column(db.String(100), unique=False, nullable=False)
    created_date = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, nullable=True, onupdate=datetime.now)

"""
CSV Download
"""

   
@app.route('/download')
def download():
    try:
        scrap_data = ScrapData.query.filter(ScrapData.id).order_by(ScrapData.created_date.desc()).first()
        response = scrap_data.scrapped
        data = json.loads(response)
        df = pd.DataFrame.from_dict(data)
        df.to_csv('data.csv', encoding='utf-8', index=True)   
        
    except Exception as e:
        print(e)
    return send_file('data.csv', as_attachment=True)


@app.route("/download/report/<int:id>")
@login_required
def download_report(id):
    try:
        scrap_data = ScrapData.query.get(id)
        response = scrap_data.scrapped
        data = json.loads(response)
        df = pd.DataFrame.from_dict(data)
        df.to_csv('data.csv', encoding='utf-8', index=True)   
    except Exception as e:
        print(e)
    return send_file('data.csv', as_attachment=True)

"""
Login manager
"""

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
with app.app_context():
    db.create_all()

"""
web-driver
"""
options = webdriver.ChromeOptions()
options.headless = True
options.add_argument('--no-sandbox')
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
options.add_argument("no-sandbox")
options.add_argument("disable-infobars")
options.add_argument("disable-dev-shm-usage")
options.add_argument("disable-browser-side-navigation")
options.add_argument("disable-gpu")
options.add_argument("--dns-prefetch-disable")
options.add_argument("disable-extensions")
options.add_argument("force-device-scale-factor=1")
options.add_argument("enable-features=NetworkServiceInProcess")
options.add_argument("--aggressive-cache-discard")
options.add_argument("--disable-cache")
options.add_argument("--disable-application-cache")
options.add_argument("--disable-offline-load-stale-cache")
options.add_argument("start-maximized")
options.add_argument("lang=de")
options.add_argument("allow-running-insecure-content")
options.add_argument("inprivate")


"""
Dice Crawler
"""

@celery.task(bind=True)
def extract_dice_jobs(self, web, tech, location, user_id, page=1):
   
    with app.app_context():
        driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
        # driver=webdriver.Remote(command_executor='http://chrome:4444/wd/hub',desired_capabilities=DesiredCapabilities.CHROME, options=options)
        time.sleep(3)
        job_titles_list, company_name_list, location_list, job_types_list = [], [], [], []
        job_posted_dates_list, job_descriptions_list = [], []
        verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
        adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
        noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
        message = ''
        for k in range(1, int(page)):
            URL = f"http://www.dice.com/jobs?q={tech}&location={location}&radius=30&radiusUnit=mi&page={k}&pageSize=20&language=en&eid=S2Q_,bw_1"
            driver.get(URL)
            try:
                input = driver.find_element(By.ID, "typeaheadInput")
                input.click()
            except:
                time.sleep(5)

            job_titles = driver.find_elements(By.CLASS_NAME, "card-title-link")
            company_name = driver.find_elements(
                By.XPATH, '//div[@class="card-company"]/a')
            job_locations = driver.find_elements(
                By.CLASS_NAME, "search-result-location")
            job_types = driver.find_elements(
                By.XPATH, '//span[@data-cy="search-result-employment-type"]')
            job_posted_dates = driver.find_elements(By.CLASS_NAME, "posted-date")
            job_descriptions = driver.find_elements(By.CLASS_NAME, "card-description")

            # company_name
            for i in company_name:
                company_name_list.append(i.text)

            # job titles list
            for i in job_titles:
                job_titles_list.append(i.text)

            # #locations
            for i in job_locations:
                location_list.append(i.text)

            # job types
            for i in job_types:
                job_types_list.append(i.text)

            # job posted dates
            for i in job_posted_dates:
                job_posted_dates_list.append(i.text)

            # job_descriptions
            for i in job_descriptions:
                job_descriptions_list.append(i.text)
            #progress_recorder.set_progress(k+1, page,f'on iteration {k}')
        
            df = pd.DataFrame()
            df['Job Title'] = job_titles_list
            df['Company Name'] = company_name_list
            df['description'] = job_descriptions_list
            df['Posted Date'] = job_posted_dates_list
            df['Job Type'] = job_types_list
            df['Location'] = location_list
            
            if not message or random.random() < 0.25:
                message = '{0} {1} {2}...'.format(random.choice(verb),
                                                random.choice(adjective),
                                                random.choice(noun))
            self.update_state(state='PROGRESS', meta={'current': k, 'total': page, 'status': message})
        json_data = df.to_json()
        parsed = json.loads(json_data)
        scrap_data = ScrapData(user_id=user_id, web=web, keywords=tech, scrapped=json.dumps(parsed))
        db.session.add(scrap_data)
        db.session.commit()
        return {'current': 100, 'total': 100, 'status': 'Task completed!'}

"""
Indeed.com crawler
"""

job_posted_dates_list, job_descriptions_list = [], []
description_list, company_name_list, designation_list, salary_list, company_url = [], [], [], [], []
location_list, qualification_list = [], []
BASE_URL = 'https://in.indeed.com'


@celery.task(bind=True)
def scrap_details(self, tech, location, page, web, user_id):
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(),options=options)
    job_detail_links = []
    with app.app_context():
        def get_job_detail_links(tech, location, page):

            for page in range(0, page):
                time.sleep(5)
                URL = f"https://in.indeed.com/jobs?q={tech}&l={location}&start={page*10}"
                try:
                    driver.get(URL)
                except WebDriverException:
                    print("page down")

                soup = BeautifulSoup(driver.page_source, 'lxml')

                for outer_artical in soup.findAll(attrs={'class': "css-1m4cuuf e37uo190"}):
                    for inner_links in outer_artical.findAll(
                            attrs={'class': "jobTitle jobTitle-newJob css-bdjp2m eu4oa1w0"}):
                        job_detail_links.append(
                            f"{BASE_URL}{inner_links.a.get('href')}")

        message = ''
        get_job_detail_links(tech, location, page)
        time.sleep(2)
        for link in range(len(job_detail_links)):
            time.sleep(5)
            driver.get(job_detail_links[link])
            soup = BeautifulSoup(driver.page_source, 'lxml')
            a = soup.findAll(
                attrs={'class': "jobsearch-InlineCompanyRating-companyHeader"})
            company_name_list.append(a[1].text)
            try:
                company_url.append(a[1].a.get('href'))
            except:
                company_url.append('NA')

            salary = soup.findAll(
                attrs={'class': "jobsearch-JobMetadataHeader-item"})
            if salary:
                for i in salary:
                    x = i.find('span')
                    if x:
                        salary_list.append(x.text)
                    else:
                        salary_list.append('NA')
            else:
                salary_list.append('NA')

            description = soup.findAll(
                attrs={'class': "jobsearch-jobDescriptionText"})

            if description:
                for i in description:
                    description_list.append(i.text)
            else:
                description_list.append('NA')

            designation = soup.findAll(
                attrs={'class': 'jobsearch-JobInfoHeader-title-container'})
            if designation:
                designation_list.append(designation[0].text)
            else:
                designation_list.append('NA')
            for Tag in soup.find_all('div', class_="icl-Ratings-count"):
                Tag.decompose()
            for Tag in soup.find_all('div', class_="jobsearch-CompanyReview--heading"):
                Tag.decompose()
            location = soup.findAll(
                attrs={'class': "jobsearch-CompanyInfoWithoutHeaderImage"})
            if location:
                for i in location:
                    location_list.append(i.text)
            else:
                location_list.append('NA')

                # Qualification
            qualification = soup.findAll(
                attrs={"class": 'jobsearch-ReqAndQualSection-item--wrapper'})
            if qualification:
                for i in qualification:
                    qualification_list.append(i.text)
            else:
                qualification_list.append('NA')


            df = pd.DataFrame()
            df['Company Name'] = company_name_list
            df['Company_url'] = company_url
            df['salary'] = salary_list
            # df['description_list'] = description_list
            df['designation_list'] = designation_list
            df['location_list'] = location_list
            df['qualification_list'] = qualification_list
            verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
            adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
            noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']

            if not message or random.random() < 0.25:
                message = '{0} {1} {2}...'.format(random.choice(verb),
                                            random.choice(adjective),
                                            random.choice(noun))
            self.update_state(state='PROGRESS', meta={'current': link, 'total': len(job_detail_links), 'status': message})
        json_data = df.to_json()
        parsed = json.loads(json_data)
        scrap_data = ScrapData(user_id=user_id, web=web, keywords=tech, scrapped=json.dumps(parsed))
        db.session.add(scrap_data)
        db.session.commit()
        return {'current': 100, 'total': 100, 'status': 'Task completed!'}


"""
Naukari.com Crawler
"""
description_list_naukari, company_name_list_naukari, designation_list_naukari, salary_list_naukari, company_url_naukari = [], [], [], [], []
location_list_naukari, qualification_list_naukari = [], []
BASE_URL_naukari = 'https://www.naukri.com/'


@celery.task(bind=True)
def scrap_naukari(self, tech, location, page, web, user_id):
    FILE_NAME = 'naukri.csv'
    job_detail_links_naukari = []
    driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
    with app.app_context():
        def get_job_detail_links_naukari(tech, location, page):

            for page_no in range(0, page):
                URL = f"https://www.naukri.com/python-jobs-in-{location}-{page_no}?k={tech}&l={location}"
                driver.get(URL)
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, 'lxml')

            for outer_artical in soup.findAll(attrs={'class': "jobTuple bgWhite br4 mb-8"}):
                for inner_links in outer_artical.find(attrs={'class': "jobTupleHeader"}).findAll(
                        attrs={'class': "title fw500 ellipsis"}):
                    job_detail_links_naukari.append(inner_links.get('href'))
        get_job_detail_links_naukari(tech, location, page)
        verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
        adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
        noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
        message = ''
        designation_list_naukari, company_name_list_naukari, experience_list, salary_list__naukari = [], [], [], []
        location_list__naukari, job_description_list, role_list, industry_type_list = [], [], [], []
        functional_area_list, employment_type_list, role_category_list, education_list = [], [], [], []
        key_skill_list, about_company_list, address_list, post_by_list = [], [], [], []
        post_date_list, website_list, url_list = [], [], []

        for link in range(len(job_detail_links_naukari)):
            time.sleep(5)
            driver.get(job_detail_links_naukari[link])
            soup = BeautifulSoup(driver.page_source, 'lxml')
            if soup.find(attrs={'class': "salary"}) == None or soup.find(attrs={'class': 'loc'}) == "Remote":
                continue
            else:
                company_name_list_naukari.append("NA" if soup.find(attrs={'class': "jd-header-comp-name"}) == None else soup.find(
                    attrs={'class': "jd-header-comp-name"}).text)
                experience_list.append(
                    "NA" if soup.find(attrs={'class': "exp"}) == None else soup.find(attrs={'class': "exp"}).text)
                salary_list_naukari.append(
                    "NA" if soup.find(attrs={'class': "salary"}) == None else soup.find(attrs={'class': "salary"}).text)
                loca = []
                location = (
                    "NA" if soup.find(attrs={'class': 'loc'}) == None else soup.find(attrs={'class': 'loc'}).findAll('a'))
                for i in location:
                    try:
                        loca.append(i.text)
                    except AttributeError:
                        loca.append(i)
                    except:
                        loca.append(i)

                location_list_naukari.append(",".join(loca))

                designation_list_naukari.append("NA" if soup.find(attrs={'class': "jd-header-title"}) == None else soup.find(
                    attrs={'class': "jd-header-title"}).text)
                job_description_list.append(
                    "NA" if soup.find(attrs={'class': "job-desc"}) == None else soup.find(attrs={'class': "job-desc"}).text)
                post_date_list.append(["NA"] if soup.find(attrs={'class': "jd-stats"}) == None else
                                    [i for i in soup.find(attrs={'class': "jd-stats"})][0].text.split(':')[1])
                try:
                    website_list.append(
                        "NA" if soup.find(attrs={'class': "jd-header-comp-name"}).contents[0]['href'] == None else
                        soup.find(attrs={'class': "jd-header-comp-name"}).contents[0]['href'])
                except KeyError or ValueError:
                    website_list.append("NA")
                except:
                    website_list.append("NA")
                try:
                    url_list.append(
                        "NA" if soup.find(attrs={'class': "jd-header-comp-name"}).contents[0]['href'] == None else
                        soup.find(attrs={'class': "jd-header-comp-name"}).contents[0]['href'])
                except KeyError or ValueError:
                    website_list.append("NA")
                except:
                    website_list.append("NA")

                details = []
                try:
                    for i in soup.find(attrs={'class': "other-details"}).findAll(attrs={'class': "details"}):
                        details.append(i.text)
                    role_list.append(details[0].replace('Role', ''))
                    industry_type_list.append(details[1].replace('Industry Type', ''))
                    functional_area_list.append(details[2].replace('Functional Area', ''))
                    employment_type_list.append(details[3].replace('Employment Type', ''))
                    role_category_list.append(details[4].replace('Role Category', ''))

                    qual = []
                    for i in soup.find(attrs={'class': "education"}).findAll(attrs={'class': 'details'}):
                        qual.append(i.text)
                    education_list.append(qual)

                    sk = []
                    for i in soup.find(attrs={'class': "key-skill"}).findAll('a'):
                        sk.append(i.text)
                    key_skill_list.append(",".join(sk))

                    if soup.find(attrs={'class': "name-designation"}) == None:
                        post_by_list.append("NA")
                    else:
                        post_by_list.append(soup.find(attrs={'class': "name-designation"}).text)

                    if soup.find(attrs={'class': "about-company"}) == None:
                        about_company_list.append("NA")
                    else:
                        address_list.append("NA" if soup.find(attrs={'class': "about-company"}).find(
                            attrs={'class': "comp-info-detail"}) == None else soup.find(
                            attrs={'class': "about-company"}).find(attrs={'class': "comp-info-detail"}).text)
                        about_company_list.append(soup.find(attrs={'class': "about-company"}).find(
                            attrs={'class': "detail dang-inner-html"}).text)
                except:
                    pass
                if not message or random.random() < 0.25:
                    message = '{0} {1} {2}...'.format(random.choice(verb),
                                                    random.choice(adjective),
                                                    random.choice(noun))
                self.update_state(state='PROGRESS', meta={'current': link, 'total': len(job_detail_links_naukari), 'status': message})


        df = pd.DataFrame()
        df['Designation'] = pd.Series(designation_list_naukari)
        df['Company Name'] = pd.Series(company_name_list_naukari)
        df['Salary'] = pd.Series(salary_list_naukari)
        df['Experience'] = pd.Series(experience_list)
        df['Location'] = pd.Series(location_list_naukari)
        df['Role'] = pd.Series(role_list)
        df['Functional Area'] = pd.Series(functional_area_list)
        df['Employment Type'] = pd.Series(employment_type_list)
        df['Role Category'] = pd.Series(role_category_list)
        df['Address'] = pd.Series(address_list)
        df['Post By'] = pd.Series(post_by_list)
        df['Post Date'] = pd.Series(post_date_list)
        df['Website'] = pd.Series(website_list)
        df['Url'] = pd.Series(url_list)
        df['Job Description'] = pd.Series(job_description_list)
        df['About Company'] = pd.Series(about_company_list)
        json_data = df.to_json()
        parsed = json.loads(json_data)
        scrap_data = ScrapData(user_id=user_id, web=web, keywords=tech, scrapped=json.dumps(parsed))
        db.session.add(scrap_data)
        db.session.commit()
        return {'current': 100, 'total': 100, 'status': 'Task completed!'}




@app.route("/", endpoint="1")
@app.route("/home", endpoint="1")
@login_required
def home():
    user = current_user.id
    name = current_user.first_name
    results = ScrapData.query.filter(ScrapData.user_id==user).order_by(ScrapData.created_date.desc()).paginate(page=1,per_page=9)
    return render_template("home.html", results=results)


@app.route("/signup", methods=('GET', 'POST'))
def signup():
    msg = ''
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        session["email"] = request.form['email']
        contact = request.form['contact']
        password = request.form['password']
        account = User.query.filter_by(email=email).first()

        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', firstname):
            msg = 'Username must contain only characters and numbers !'
        elif not firstname or not lastname or not email or not contact or not password:
            msg = 'Please fill out the form !'
        else:
            hashed_password = generate_password_hash(
                password=password, method='sha256')

            new_user = User(first_name=firstname,
                            last_name=lastname,
                            email=email,
                            mobile=contact,
                            password=hashed_password,
                            status='ACTIVE')
            db.session.add(new_user)
            db.session.commit()

            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('signup.html', msg=msg)


@ app.route("/login", methods=['GET','POST'])
def login():
    msg = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email,status='ACTIVE').first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect('/home')
               
            else:
                error = "Wrong password"
                return render_template("login.html", name="login", error=error)
        else:
            error = "User Does Not Exist"
            return render_template("login.html", name="login", error=error)
    else:
        return render_template("login.html", name="login")


@app.route("/logout", endpoint='2')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect('/login')


@app.route("/search", endpoint="3", methods=['GET', 'POST'])
@login_required
def search():
    web = request.args.get("web")
    session["web"] = request.args.get("web")
    tech = request.args.get("tech", "python")
    page = request.args.get("pages", "1")
    location = request.args.get("location", "india")
    df = None
    name = None
    task_id = None
    if page == None:
        page = 5
    page = int(page)
    if web == None or tech == None:
        return redirect("/")
    user_id = current_user.id
    if web == "indeed":
        task = scrap_details.apply_async([tech, location, page, web, user_id])
        session['task_id'] = task.id
        return jsonify({}), 202, {'Location': url_for('taskstatus', task_id=task.id)}
    if web == "dice":
        task = extract_dice_jobs.apply_async([web, tech, location, user_id, page])
        session['task_id'] = task.id
        return jsonify({}), 202, {'Location': url_for('taskstatus', task_id=task.id)}
    if web == "naukri":
        task = scrap_naukari.apply_async([tech, location, page, web, user_id])
        session['task_id'] = task.id
        return jsonify({}), 202, {'Location': url_for('taskstatus', task_id=task.id)}



@app.route('/status/<task_id>')
def taskstatus(task_id):
    web = session.get("web")
    task = None
    if web == 'indeed':
        task = scrap_details.AsyncResult(task_id)
    elif web == 'dice':
        task = extract_dice_jobs.AsyncResult(task_id)

    elif web == 'naukri':
        task = scrap_naukari.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
            }
    return jsonify(response)


@app.route("/export")
def export():
    web = session.get("web")
    csv_dir = "/api/static/"
    if web == "indeed":
        csv_file = 'indeed.csv'
        csv_path = os.path.join(csv_dir, csv_file)
        return send_file(csv_path, as_attachment=True)
    elif web == "dice":
        csv_file = 'dice.csv'
        csv_path = os.path.join(csv_dir, csv_file)
        save_dice_data_to_db()
        return send_file(csv_path, as_attachment=True)
    elif web == "naukri":
        csv_file = 'naukri.csv'
        csv_path = os.path.join(csv_dir, csv_file)
        return send_file(csv_path, as_attachment=True)
    else:
        return redirect("/")


if __name__ == "__main__":
    sess.init_app(app)
    app.run(debug=True, host="0.0.0.0")
