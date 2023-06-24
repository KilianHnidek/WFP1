from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, List

import docker
import time
import schedule
import re
from flask import Flask, Response
from prometheus_client import generate_latest, Counter, REGISTRY
import requests
from discord.ext import commands
import discord
from enum import Enum, auto

app = Flask(__name__)

# Define your metrics
REQUESTS = Counter('hello_worlds_total', 'Hello Worlds requested.')

# Secret token for authenticated commands
# noinspection SpellCheckingInspection
SECRET_TOKEN = 'SECRET'

# Mapping container names to their metrics ports
metrics_ports = {
    'database': 3306,
    'frontend': 4200,
    'backend': 5000,
    'scraper': 8080,
    'predictor': 7000
}

# Regular expression pattern for checking container names
CONTAINER_NAME_PATTERN = re.compile(r'^[\w-]+$')

# Regular expression pattern for checking frequency
FREQUENCY_PATTERN = re.compile(r'^(daily|hourly|weekly|[0-9]+(min|hour))$')

# Regular expression pattern for checking specific time
TIME_PATTERN = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')


@app.route('/management/hello')
def hello():
    REQUESTS.inc()  # increment counter
    return "Hello World!"


@app.route('/management/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(REGISTRY), mimetype='text/plain')


class JobStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPED = auto()


class Job:
    def __init__(self, job_name: str, job_description: str, containers: List[str], schedule_time: str,
                 frequency: str, container_routes: Dict[str, str], container_payloads: Dict[str, Dict[str, str]]):
        self.job_name = job_name
        self.job_description = job_description
        self.containers = containers
        self.schedule_time = schedule_time
        self.frequency = frequency
        self.container_routes = container_routes
        self.container_payloads = container_payloads

        self.status = JobStatus.IDLE
        self.last_run = None

    def __str__(self):
        return f'Job Name: {self.job_name}\n' \
               f'Job Description: {self.job_description}\n' \
               f'Containers: {self.containers}\n' \
               f'Schedule Time: {self.schedule_time}\n' \
               f'Frequency: {self.frequency}\n' \
               f'Container Routes: {self.container_routes}\n' \
               f'Container Payloads: {self.container_payloads}\n'

    def start(self, management: 'Management') -> None:
        print(f"Starting job {self.job_name}...\n")
        management.start_containers(self.containers)
        for container in self.containers:
            route = self.container_routes.get(container)
            payload = self.container_payloads.get(container)
            if route and payload:
                response = requests.post(f'http://{container}:{metrics_ports[container]}{route}', json=payload)
                print(f"Started process in container {container} with response {response}\n")
        self.status = JobStatus.RUNNING
        self.last_run = datetime.now()
        print(f"Job {self.job_name} started.\n")

    def stop(self, management: 'Management') -> None:
        print(f"Stopping job {self.job_name}...\n")
        management.stop_containers(self.containers)
        self.status = JobStatus.STOPPED
        print(f"Job {self.job_name} stopped.\n")

    def run(self, management: 'Management') -> None:
        if self.status == JobStatus.IDLE:
            self.start(management)
        else:
            print(f"Job {self.job_name} is already running.\n")


class Management:
    """
    The Management class is used to manage Docker containers.
    It includes methods for creating, starting, and stopping Docker containers,
    as well as retrieving container metrics and info.
    """

    def __init__(self):
        self.client = docker.from_env()
        self.jobs = {}
        self.job_status = {}

        """
        Pre-defined jobs -> contain all container necessary for
        the workflow, and other stuff..
        """
        self.create_job(
            job_name="website",
            job_description="Stops all frontend and backend services during non-business hours.",
            containers=['frontend', 'backend'],
            schedule_time="17:26",
            frequency="daily",
            container_routes={},
            container_payloads={}
        )

        self.create_job(
            job_name="database",
            job_description="Performs maintenance on database service weekly.",
            containers=['db'],
            schedule_time="17:27",
            frequency="weekly",
            container_routes={},
            container_payloads={}
        )

        self.create_job(
            job_name="scraping",
            job_description="Job to scrape the data",
            containers=["db", "scraper"],
            schedule_time="17:28",
            frequency="daily",
            container_routes={"scraper": "/scraper/scrape"},
            container_payloads={
                "scraper": {
                    "city": "Vienna",
                    "date": "2024-07-15",
                    "nights": 2,
                    "guests": 2,
                    "rooms": 2,
                    "accommodation": "Hotel",
                }
            }
        )

    """
    Every job does have a scheduled time and frequency
    This method continuously checks if a jobs should start
    """

    def check_jobs(self, debug=True) -> None:
        while True:
            current_time = datetime.now()

            if debug:
                print(f"Current time: {current_time.strftime('%H:%M')}\n")
                print(self.jobs.values())

            for job in self.jobs.values():
                try:
                    scheduled_time = datetime.strptime(job.schedule_time, '%H:%M')
                    scheduled_time = scheduled_time.replace(year=current_time.year, month=current_time.month,
                                                            day=current_time.day)

                    if debug:
                        print(f"Scheduled time for job {job.job_name}: {scheduled_time.strftime('%H:%M')}\n")

                    # Compare the current time with the scheduled time
                    time_difference = int((current_time - scheduled_time).total_seconds() / 60)
                    if -3 <= time_difference <= 3 and current_time.hour == scheduled_time.hour:
                        # Parse last run time to a string for comparison
                        last_run_str = job.last_run.strftime('%H:%M') if job.last_run else None
                        if job.last_run is None or job.last_run.date() != current_time.date() or \
                                last_run_str != scheduled_time.strftime('%H:%M'):
                            print(f"Attempting to start job {job.job_name} at {current_time}\n")
                            job.run(self)
                            job.last_run = current_time
                        else:
                            print(f"Job {job.job_name} has already been run today.\n")
                    else:
                        print(f"Job {job.job_name} is not scheduled to run at this time.\n")
                except Exception as e:
                    print(f"Error occurred with job {job.job_name}. Exception: {e}\n")
            time.sleep(15)

    @staticmethod
    def get_container_metrics(container_name: str) -> str | None:
        if container_name in metrics_ports:
            try:
                response = requests.get(f'http://{container_name}:{metrics_ports[container_name]}/metrics')
                return response.text
            except Exception as e:
                print(f"Failed to get container metrics. Exception: {str(e)}\n")
        return None

    """
    This method is used to create jobs for both pre-defined
    and those requested by the user via the discord bot
    """

    def create_job(self, job_name, job_description, containers, schedule_time, frequency, container_routes,
                   container_payloads):
        # First, ensure that the job doesn't involve a container that should always be running
        for container_name in containers:
            if container_name in ['management', 'proxy']:
                print("Cannot create a job for 'management' or 'proxy'. These should always be running.\n")
                return

        # Create a Job object
        new_job = Job(job_name, job_description, containers, schedule_time, frequency, container_routes or {},
                      container_payloads or {})

        # Add the job to the job dictionary
        self.jobs[job_name] = new_job
        new_job.status = JobStatus.IDLE

        # Schedule the new job
        if frequency == "daily":
            schedule.every(1).day.at(schedule_time).do(self.check_jobs)
        elif frequency == "weekly":
            schedule.every(7).days.at(schedule_time).do(self.check_jobs)

    def start_containers(self, containers: list[str]) -> None:
        """
        Start multiple containers.
        """
        for container_name in containers:
            if container_name in ['management', 'proxy']:
                print("Cannot start 'management' or 'proxy'. These should always be running.\n")
                continue
            try:
                container = self.client.containers.get(container_name)
                print(container)
                print(container.status)
                if container.status == "running":
                    print(f"Container {container_name} is already running.\n")
                else:
                    container.start()
                    print(f"Container {container_name} has been started.")
                    if container_name != 'proxy' and container_name != 'management':
                        while container.status != "running":
                            container.reload()
                            time.sleep(10)
                        print(f"Container {container_name} is now running.")
            except Exception as e:
                print(f"Failed to start container {container_name}. Exception: {str(e)}\n")

    def stop_containers(self, containers: list[str]) -> None:
        """
        Stop multiple containers.
        """
        for container_name in containers:
            if container_name in ['management', 'proxy']:
                print("Cannot stop 'management' or 'proxy'. These should always be running.\n")
                continue
            try:
                container = self.client.containers.get(container_name)
                print(container.status)
                if container.status != "running":
                    print(f"Container {container_name} is not running.\n")
                else:
                    container.stop()
                    print(f"Container {container_name} has been stopped.\n")
            except Exception as e:
                print(f"Failed to stop container {container_name}. Exception: {str(e)}\n")

    """
    A thread does check in a set interval for
    jobs that are not in the running state and
    consequently turns of specified containers
    to save resources
    """

    def stop_unused_containers(self) -> None:
        active_containers = set()
        for job in self.jobs.values():
            if job.status == JobStatus.RUNNING:
                active_containers.update(job.containers)

        # Exclude containers that should always be running
        excluded_containers = ['management', 'proxy']
        active_containers.difference_update(excluded_containers)

        all_containers = set([c.name for c in self.client.containers.list(all=True)])

        containers_to_stop = list(all_containers - active_containers)
        self.stop_containers(containers_to_stop)
        for container_name in containers_to_stop:
            print(f"Stopped container {container_name}")

    """
    Used by the discord bot, a user can retrieve
    information's about each container
    """
    def get_container_info(self, container_name: str) -> dict[str, str | any] | None:
        try:
            container = self.client.containers.get(container_name)
            return {
                "name": container.name,
                "status": container.status,
                "image": str(container.image),
                "created": container.attrs['Created'],
                "network_settings": container.attrs['NetworkSettings']
            }
        except Exception as e:
            print(f"Failed to get container info. Exception: {str(e)}\n")
            return None


@app.route('/management/start_job/<string:job_name>', methods=['POST'])
def start_job(job_name) -> tuple[str, int]:
    if job_name not in management.jobs:
        return 'Job not found', 404
    job = management.jobs[job_name]
    job.start(management)
    return f'Started job {job_name}', 200


@app.route('/management/stop_job/<string:job_name>', methods=['POST'])
def stop_job(job_name) -> tuple[str, int]:
    if job_name not in management.jobs:
        return 'Job not found', 404
    job = management.jobs[job_name]
    job.stop(management)
    return f'Stopped job {job_name}', 200


@app.route('/management/force_run_job/<string:job_name>', methods=['POST'])
def force_run_job(job_name) -> tuple[str, int]:
    management.force_run_job(job_name)
    return f"Forced immediate run of job '{job_name}'", 200


@app.route('/management/jobs', methods=['GET'])
def get_jobs():
    jobs = {name: str(job[0]) for name, job in management.jobs.items()}  # job[0] is the Job instance
    return {"jobs": jobs}


def discord_bot() -> None:
    intents = discord.Intents().all()
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.command()
    async def add(ctx, job_name, job_description, container_name, frequency, specific_time):
        if CONTAINER_NAME_PATTERN.match(container_name) and FREQUENCY_PATTERN.match(frequency) and TIME_PATTERN.match(
                specific_time):
            try:
                management.create_job(job_name, job_description, [container_name], specific_time, frequency)
                await ctx.send(f'Added job {job_name} with frequency {frequency} at time {specific_time}')
            except Exception as e:
                await ctx.send(f"Failed to add job. Exception: {str(e)}")
        else:
            await ctx.send('Invalid input. Please follow the correct formats.')

    @bot.command()
    async def info(ctx, container_name):
        container_info = management.get_container_info(container_name)
        if container_info:
            info_message = "\n".join([f"{k}: {v}" for k, v in container_info.items()])
            await ctx.send(f"Container Info:\n{info_message}")
        else:
            await ctx.send(f"Could not get info for {container_name}")

    @bot.command()
    async def help_info(ctx):
        help_message = '''
        !jobs
            -> lists all jobs available

        !add "job_name" "job_description" "container_name" "frequency" "specific_time"
            -> frequency: "daily" "weekly"
            -> specific_time(format): "HH:MM"
        
        !start {job_name}
        !stop {job_name}
        
        '''
        await ctx.send(help_message)

    @bot.command()
    async def start(ctx, job_name) -> None:
        response, status_code = start_job(job_name)
        if status_code == 200:
            await ctx.send(f'Started job {job_name}')
        else:
            await ctx.send(response)

    @bot.command()
    async def stop(ctx, job_name):
        response, status_code = stop_job(job_name)
        if status_code == 200:
            await ctx.send(f'Stopped job {job_name}')
        else:
            await ctx.send(response)

    @bot.command()
    async def jobs(ctx):
        j = management.jobs
        jobs_message = "\n".join([f"{name}:\n{str(job)}" for name, job in j.items()])
        await ctx.send(f"Available jobs:\n{jobs_message}")

    @bot.command()
    async def container_metrics(ctx, container_name):
        metric = Management.get_container_metrics(container_name)
        if metric:
            await ctx.send(f"Metrics for {container_name}:\n{metric}")
        else:
            await ctx.send(f"Failed to retrieve metrics for {container_name}")

    bot.run('SECRET')


def run_schedule() -> None:
    while True:
        print("Checking for scheduled jobs...")
        schedule.run_pending()
        print(schedule.jobs)
        time.sleep(1)


if __name__ == "__main__":
    management = Management()

    # Schedule the jobs
    for job in management.jobs.values():
        if job.frequency == "daily":
            schedule.every(1).day.at(job.schedule_time).do(management.check_jobs)
        elif job.frequency == "weekly":
            schedule.every(7).days.at(job.schedule_time).do(management.check_jobs)

    # Start the scheduler in a new thread
    Thread(target=run_schedule).start()
    # Starts the discord bot
    Thread(target=discord_bot).start()

    # Hide system containers
    hidden_containers = ['management', 'proxy', 'prometheus', 'grafana']
    management.jobs = {k: v for k, v in management.jobs.items() if k not in hidden_containers}

    # Schedule the stop_unused_containers method to run every X minutes
    schedule.every(15).minutes.do(management.stop_unused_containers)

    # Run the Flask server
    app.run(host='0.0.0.0', port=2000)
