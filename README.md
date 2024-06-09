# Trinnov Remote

Send HTTP calls to control your Trinnov processor (tested with JBL Synthesis SDP-75)

![image](https://github.com/Morveus/TrinnovRemote/assets/2972468/03382891-495b-46df-a59c-17ac58ab1d11)

This is a simple Python application designed to run in a home automation system. 

# Current status
🟢 Reverse engineering Trinnov's websocket from the amplifier's internal webpage (why the leading byte arrays and the 15 trailing zeroes in the volume variable ?)
🟢 First iteration (volume up/down/dim/undim)
🟠 Add a "set volume" call
🟠 Get variables (IP, default volume, port) from env (Docker, Kubernetes) 
🔴 Add sources switch
🔴 Make calls fully async
🔴 Get volume from the amp at startup, and update it from time to time

The app provides a web server with endpoints to control the volume and source of an amplifier via its WebSocket messages.

Since most home automation systems work best with HTTP calls, there it is.

It is still a WIP as I'm building a new home theater (and the home around it) that should be ready in 2025. I hope this project will be fully useable and integrated by then. 

## Features

- **Volume Control Endpoints:**
  - `/volume/plus`: Increase the volume.
  - `/volume/minus`: Decrease the volume.
  - `/volume/mute`: Mute the volume.
  - `/volume/dim`: Dim the volume.
  - `/volume/undim`: Undim the volume.

- **Source Control Endpoints:**
  - `/source/hdmi1`: Switch to HDMI1.
  - `/source/hdmi2`: Switch to HDMI2.
  - `/source/hdmi3`: Switch to HDMI3.
  - `/source/hdmi4`: Switch to HDMI4.

## WebSocket Communication

When any of the endpoints are called, a message is sent to the amplifier via a WebSocket connection.

## Environment Variables

- `AMPLIFIER_IP`: The IP address of the amplifier (default is mine, `192.168.1.91`).

## Usage

### Prerequisites

Ensure you have at least Python / PIP installed, docker if you wish to run this as a container (mine is running in a Kubernetes cluster)

### Building the Docker Image

1. Build the Docker image:
    ```bash
    docker build -t your-dockerhub-username/trinnov-remote:latest .
    ```

2. Push the Docker image to Docker Hub:
    ```bash
    docker push your-dockerhub-username/trinnov-remote:latest
    ```

### Deploying to Kubernetes

1. Apply the Kubernetes deployment:
    ```bash
    kubectl apply -f deployment.yaml
    ```

### Running the Application Locally

1. Install the required Python packages:
    ```bash
    pip install Flask websockets
    ```

2. Run the application:
    ```bash
    python app.py
    ```

### Endpoints

#### Volume Control

- `GET /volume/plus`: Increase the volume.
- `GET /volume/minus`: Decrease the volume.
- `GET /volume/mute`: Mute the volume.
- `GET /volume/dim`: Dim the volume.
- `GET /volume/undim`: Undim the volume.

#### Source Control

- `GET /source/hdmi1`: Switch to HDMI1.
- `GET /source/hdmi2`: Switch to HDMI2.
- `GET /source/hdmi3`: Switch to HDMI3.
- `GET /source/hdmi4`: Switch to HDMI4.

## Example

To increase the volume:
```bash
curl http://your-server-ip:5555/volume/plus
```

To change the source to HDMI1:
```bash
curl http://your-server-ip:5555/source/hdmi1
```


## Notes

Volume is set to -60 when the app starts. The app being the "source of truth" in my system. Feel free to modify the code to suit your needs.


# Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
