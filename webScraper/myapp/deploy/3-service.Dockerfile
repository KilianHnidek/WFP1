# Use an official Node runtime as a parent image
FROM node:16.13-slim AS builder

# Set the working directory in the container to /app
WORKDIR /frontend

# Copy package.json and package-lock.json to the working directory
COPY ./website/frontend/package*.json ./

# Install Angular CLI and npm dependencies
RUN npm install -g npm@8.3.1 \
    && npm install -g @angular/cli@12.0.0 \
    && npm install

# Copy the current directory contents into the container at /app
COPY ./website/frontend .

FROM node:16.13-slim AS runtime

# Copy the node_modules folder and other build content
COPY --from=builder /frontend /frontend
# Copy the global npm packages
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin /usr/local/bin

# Set the working directory in the container to /app
WORKDIR /frontend

# Make port 4200 available to the world outside this container
EXPOSE 4200

# Set the PATH to include global npm packages
ENV PATH="/usr/local/lib/node_modules/.bin:${PATH}"

# Set the entrypoint to serve the app
ENTRYPOINT ["ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--proxy-config", "proxy.conf.json"]

