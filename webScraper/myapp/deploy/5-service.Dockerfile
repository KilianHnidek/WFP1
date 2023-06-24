FROM my-base-image:latest AS builder

# Set environment variable for timezone
ENV TZ=Europe/Vienna

# Add tzdata package for timezone manipulation
RUN apt-get update && apt-get install -y tzdata

# Set timezone as specified by TZ environment variable
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY /myapp/deploy/5-service.requirements.txt /5-service.requirements.txt

RUN /venv/bin/pip install --disable-pip-version-check --no-cache-dir -r /5-service.requirements.txt

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

FROM gcr.io/distroless/python3-debian11 AS runtime

# Copy timezone info from builder
COPY --from=builder /etc/localtime /etc/localtime
COPY --from=builder /etc/timezone /etc/timezone

COPY ./predictor /predictor
WORKDIR /predictor

COPY --from=builder /venv /venv

ENTRYPOINT ["/venv/bin/python3", "predictor_classic.py"]
