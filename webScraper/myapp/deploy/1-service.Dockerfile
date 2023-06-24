FROM my-base-image:latest AS build-venv

# Set environment variable for timezone
ENV TZ=Europe/Vienna

# Add tzdata package for timezone manipulation
RUN apt-get update && apt-get install -y tzdata

# Set timezone as specified by TZ environment variable
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./myapp/deploy/1-service.requirements.txt /1-service.requirements.txt

RUN /venv/bin/pip install --disable-pip-version-check --no-cache-dir -r /1-service.requirements.txt

FROM gcr.io/distroless/python3-debian11

# Copy timezone info
COPY --from=build-venv /etc/localtime /etc/localtime
COPY --from=build-venv /etc/timezone /etc/timezone

COPY /management/management.py .

COPY --from=build-venv /venv /venv

ENTRYPOINT ["/venv/bin/python3", "management.py"]
