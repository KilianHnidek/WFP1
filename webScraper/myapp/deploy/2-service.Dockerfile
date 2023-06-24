# Use a multi-stage build to separate the build-time dependencies from the runtime dependencies
FROM python:3.11.3-slim AS builder

# Add system packages required for compile time.
# Add tzdata package for timezone manipulation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    make \
    default-libmysqlclient-dev \
    tzdata

# Set environment variable for timezone
ENV TZ=Europe/Vienna

# Set timezone as specified by TZ environment variable
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create a virtual environment and activate it:
RUN python3.11 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Upgrade pip, setuptools and wheel:
RUN pip install --upgrade pip setuptools wheel

# Install the Python dependencies:
COPY ./myapp/deploy/2-service.requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r 2-service.requirements.txt

# Clean up.
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*


FROM python:3.11.3-slim AS runtime

# Copy timezone info from builder
COPY --from=builder /etc/localtime /etc/localtime
COPY --from=builder /etc/timezone /etc/timezone

# Add system packages required for runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    x11vnc \
    x11-xkb-utils \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-scalable \
    xfonts-cyrillic \
    x11-apps \
    libxss1 \
    libappindicator1 \
    libgconf-2-4 \
    libnss3 \
    libasound2 \
    libpango1.0-0 \
    libcairo2 \
    libcups2 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libxcb1

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Install Chromedriver
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# Clean up
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /tmp/chromedriver.zip

# Copy virtual environment from builder image:
COPY --from=builder /venv /venv

# Make sure we use the virtualenv:
ENV PATH="/venv/bin:$PATH"

# Copy the application:
COPY ./scraper /scraper

WORKDIR /scraper

CMD ["python3", "app.py"]
