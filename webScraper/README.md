Web Scraper Project
===

## Introduction

This project is a set of interconnected services that collectively form a data acquisition and processing system. Each service has its own specific responsibilities, runs independently in a separate Docker container, and communicates with other services as needed.

## Service Overview and Architecture

Here's a brief description of what each service does:

1. Management: Starts, stops -> controls & has the Discord Bot running
2. Scraper: Scrapes booking.com with the parameter received from the RESTful POST
3. Frontend Service: Handles user interactions. It displays the data, allows users to initiate a scraping operation, and download the dataset as an Excel table. It also triggers the prediction algorithm and displays the resulting graphs.
4. Backend: Handles requests like the download of the excel containing the scraped data
5. Predictor: Executes the prediction algorithm on the dataset stored in the database.
6. Database: Stores all the scraped data and is accessed by other services when they need to read or write data.
7. Proxy: Forwards requests based on the route 
8. Prometheus: Collects metrics
9. Grafana: Better visualization of metrics collected

##  Mermaid diagram of the system architecture:
```mermaid
graph LR;

  style proxy fill:#ffffff,stroke:#333,stroke-width:2px

  style frontend fill:#ffffff,stroke:#333,stroke-width:2px
  style backend fill:#ffffff,stroke:#333,stroke-width:2px

  style scraper fill:#ffffff,stroke:#333,stroke-width:2px
  style database fill:#ffffff,stroke:#333,stroke-width:2px
  style predictor fill:#ffffff,stroke:#333,stroke-width:2px

  style management fill:#ffffff,stroke:#333,stroke-width:2px
  style prometheus fill:#ffffff,stroke:#333,stroke-width:2px
  style grafana fill:#ffffff,stroke:#333,stroke-width:2px

        style discord_bot fill:#ffffff,stroke:#333,stroke-width:2px
        style manager fill:#ffffff,stroke:#333,stroke-width:2px
        style scheduler fill:#ffffff,stroke:#333,stroke-width:2px

  style website_container fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5
  style monitoring_container fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5
  style docker_containers fill:#ffffff,stroke:#333,stroke-width:2px

        style management_container fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5

                style management_threads fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5
  
  style remote_user fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5
  style remote fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5

  style external_services fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5
    
        style discord_service fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5
        style targets fill:#ffffff,stroke:#333,stroke-dasharray: 5, 5

  proxy("Proxy<br>80:80")
  scraper("Scraper<br>8080:8080")
  database("DB<br>3307:3306")
  predictor("Predictor<br>7000:7000")
  prometheus("Prometheus<br>9090:9090")
  grafana("Grafana<br>3000:3000")

  subgraph "docker_containers" ["Daemon Docker Engine"]
    proxy
    scraper
    database
    predictor

    subgraph "website_container" ["Website"]
      frontend("Frontend<br>4200:4200")
      backend("Backend<br>5000:5000")
    end

    subgraph "monitoring_container" ["Monitoring"]
      prometheus
      grafana
      subgraph "management_container" ["Management"]
        management("Management<br>2000:2000")
        subgraph "management_threads" ["Threads"]
          manager("Manager")
          discord_bot("Discord Bot")
          scheduler("Scheduler")
          end
      end
    end
  end

  subgraph "external_services" ["External Services"]
    subgraph "discord_service" ["Discord"]
        discord("WFP(Server)")
    end
    subgraph "targets" ["targets"]
        booking("booking.com")
    end
  end

  subgraph "remote" ["Remote"]
    subgraph "remote_user" ["User"]
        user("User")
    end
  end

  discord<-->|Discord Bot API|management
  proxy<-->|Proxy connection|scraper
  proxy<-->|Proxy connection|frontend
  proxy<-->|Proxy connection|backend
  proxy<-->|Internet connection|external_services
  scraper<-->|Database connection|database
  scraper<-->|Scraping targets|targets
  backend<-->|Database connection|database
  predictor<-->|Database connection|database
  frontend<-->|API connection|backend
  prometheus<-->|Monitoring services|proxy
  prometheus<-->|Monitoring services|management
  prometheus<-->|Monitoring services|scraper
  prometheus<-->|Monitoring services|backend
  prometheus<-->|Monitoring services|predictor
  grafana<-->|Grafana services|prometheus
  user<-->|Connection|discord
```

## Prerequisites

- Docker Desktop
  - all other necessaries are downloaded


## Installation

1. Clone the repository:
```git clone https://github.com/...```

2. Navigate to the directory:
3. Build and run the Docker services:


### change directory
...\webScraper>

```
docker build -t my-base-image:latest -f myapp/deploy/debian.base.Dockerfile .
docker build -t management:latest -f myapp/deploy/1-service.Dockerfile .
docker build -t scraper:latest -f myapp/deploy/2-service.Dockerfile .
docker build -t frontend:latest -f myapp/deploy/3-service.Dockerfile .
docker build -t backend:latest -f myapp/deploy/4-service.Dockerfile .
docker build -t predictor:latest -f myapp/deploy/5-service.Dockerfile .
```

### change directory
...\webScraper\myapp> docker compose up
...\webScraper\myapp> docker compose down
    if to be deleted

# terminal to database

inside docker:
```mysql -u root -p```




