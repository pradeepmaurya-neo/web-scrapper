Flask web-scrapper Api




```javascript
It is an API created for storing detils of different job portal in flask framework of python.
```
### EXTRAS 
```javascript
Web Scraping 
    Using Beautiful Soup

Web Automation 
    Using  Selenium Driver

```
## Getting Strated

 Installing Dependencies

  ### Python 3.7

 Follow instructions to install the latest version of python for your platform in the python docs

### Virtual Environment
We recommend working within a virtual environment whenever using Python for projects. This keeps your dependencies for each project separate and organized. Instructions for setting up a virtual environment for your platform can be found in the python docs

### PIP Dependencies
Once you have your virtual environment setup and running, install dependencies by running:

```javascript
pip install -r requirements.txt
```



This will install all of the required packages we selected within the requirements.txt file.

## python-flask-docker

Basic Python Flask app in Docker which prints the hostname and IP of the container

### Build application

Build the Docker image manually by cloning the Git repo.

```javascript
$ git clone https://github.com/pradeepmaurya-neo/web-scrapper-docker.git
$ docker build -t pradeepmaurya-neo/web-scrapper-docker .
```

### Download precreated image

You can also just download the existing image from DockerHub.


```javascript
docker pull pradeepmaurya-neo/web-scrapper-docker

```

### Run the container
Create a container from the image.

```javascript
$ docker run --name my-container -d -p 8080:8080 pradeepmaurya-neo/web-scrapper-docker
```

Now visit http://localhost:8080

```javascript
The hostname of the container is 6095273a4e9b and its IP is 172.17.0.2. 
```

### Verify the running container
Verify by checking the container ip and hostname (ID):

```javascript
$ docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' my-container
172.17.0.2
$ docker inspect -f '{{ .Config.Hostname }}' my-container
6095273a4e9b
```
### Additional Resources
Looking to learn more about Redis? Here's some useful resources:

* Chat with us and get your questions answered on the Redis Discord server.
* Subscribe to our YouTube channel.
* redis.io - Docmentation and reference materials.
* developer.redis.com - the official Redis Developer site.
* Redis University - free online Redis courses.

### flask-celery-redis
Example Flask, Celery, Flower and Redis services with Docker.

docker-compose.yml file split into the following services

* redis
* website
* celery
* flower

### Running the server

From within this directory first ensure you are working using your created virtual environment.

To run the server, execute the following within the backend folder:

Linux:

```javascript
export FLASK_APP=app.python
Flask run
```

Windows PowerShell:
```javascript
python app.py
```