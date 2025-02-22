import docker
import yaml
import time
import requests
import hashlib
import os

# Configuration
HOMEPAGE_URL = "https://home.dread.synology.me/reload"  # Adjust this if Homepage runs elsewhere
HOMEPAGE_CONFIG_PATH = "/volume1/docker/Homepage/services.yaml"  # Corrected to the path of services.yaml
HOMEPAGE_CONTAINER_NAME = "homepage"  # Name of your homepage container
CHECK_INTERVAL = 60  # check for new containers every 60 seconds

# Define container categories for Homepage widgets
CONTAINER_CATEGORIES = {
    "plex": "media",
    "jellyfin": "media",
    "radarr": "media",
    "sonarr": "media",
    "grafana": "monitoring",
    "prometheus": "monitoring",
    "pihole": "network",
    "home_assistant": "home-automation",
    "traefik": "services",
    "portainer": "services",
    "nginx": "services",  
}

# Initialize Docker client
client = docker.DockerClient(base_url='unix://var/run/docker.sock')

def update_yaml(container_data):
    """Update the services.yaml with new container data."""
    try:
        # Check file permissions
        if not os.access(HOMEPAGE_CONFIG_PATH, os.W_OK):
            print(f"No write access to {HOMEPAGE_CONFIG_PATH}", flush=True)
            return

        # Open services.yaml and read the existing data
        print(f"Opening config file: {HOMEPAGE_CONFIG_PATH}", flush=True)
        with open(HOMEPAGE_CONFIG_PATH, 'r') as file:
            config = yaml.safe_load(file)
        print(f"Current config: {config}", flush=True)

        # Ensure 'containers' exists (or whatever section you are updating in services.yaml)
        if 'containers' not in config:
            config['containers'] = []  # Ensure the section exists

        # Update config with new container data
        for name, data in container_data.items():
            print(f"Updating config for {name}...", flush=True)
            # Prevent adding duplicates
            if not any(c["name"] == name for c in config["containers"]):
                config["containers"].append({"name": name, **data})

        # Save the updated config back to the file
        print(f"Writing updated config to file: {HOMEPAGE_CONFIG_PATH}", flush=True)
        try:
            with open(HOMEPAGE_CONFIG_PATH, 'w') as file:
                yaml.dump(config, file)
                print("Write called", flush=True)
        except Exception as e:
            print(f"Write failed: {e}", flush=True)
            print("Retrying write...", flush=True)
            with open(HOMEPAGE_CONFIG_PATH, 'w') as file:
                yaml.dump(config, file)
                print("Write called on retry", flush=True)

        print("services.yaml updated successfully.", flush=True)
    except Exception as e:
        print(f"Error updating services.yaml: {e}", flush=True)

def get_category_from_labels(container):
    """Try to get category from container labels"""
    labels = container.attrs.get("Config", {}).get("Labels", {})
    for key, value in labels.items():
        if "homepage.group" in key:  # Some containers use 'homepage.group' for category
            return value.lower()
    return None  # Default to None if no label found

def get_current_containers():
    """Retrieve currently running containers and their details."""
    containers = client.containers.list()
    container_data = {}

    for container in containers:
        details = container.attrs
        name = container.name
        image = details["Config"]["Image"].split(":")[0]  # Get image name without tag
        ports = details["NetworkSettings"]["Ports"] or {}  # Ensure ports is a dictionary

        # Try to auto-detect category from labels
        category = get_category_from_labels(container) or CONTAINER_CATEGORIES.get(image.lower(), "services")

        # Extracting first exposed port (if available)
        first_port = next(iter(ports.values()), [{}])
        port_mapping = first_port[0].get("HostPort", "N/A") if first_port else "N/A"

        container_data[name] = {
            "name": name,
            "image": image,
            "category": category,
            "port": port_mapping,
        }

    return container_data

def reload_homepage():
    """Trigger Homepage to reload without restarting."""
    try:
        response = requests.post(HOMEPAGE_URL)  # Changed GET to POST here
        if response.status_code == 200:
            print("✅ Homepage reloaded successfully!", flush=True)
        else:
            print(f"❌ Failed to reload Homepage: {response.status_code}", flush=True)
    except Exception as e:
        print(f"❌ Error reloading Homepage: {e}", flush=True)

def get_file_hash(file_path):
    """Generate a hash of the file to detect changes"""
    try:
        with open(file_path, "rb") as file:
            return hashlib.md5(file.read()).hexdigest()
    except FileNotFoundError:
        return None

def update_homepage_config(new_containers):
    """Modify homepage's services.yaml only if changes are detected."""
    try:
        old_hash = get_file_hash(HOMEPAGE_CONFIG_PATH)

        # Load current config
        with open(HOMEPAGE_CONFIG_PATH, "r") as file:
            config = yaml.safe_load(file)

        # Ensure sections exist
        for category in set(CONTAINER_CATEGORIES.values()):
            if category not in config:
                config[category] = []  # Ensure the category section exists

        # Add new containers if not already in config
        for name, details in new_containers.items():
            section = details["category"]  # Get correct category section

            if not any(service.get("name") == name for service in config[section]):
                config[section].append({
                    "name": details["name"],
                    "url": f"http://localhost:{details['port']}" if details["port"] != "N/A" else "N/A",
                    "icon": details["image"],
                })
                print(f"✅ Added {name} to Homepage under {section} category.", flush=True)

        # Save updated config
        with open(HOMEPAGE_CONFIG_PATH, "w") as file:
            yaml.safe_dump(config, file)

        # Only reload Homepage if config changed
        new_hash = get_file_hash(HOMEPAGE_CONFIG_PATH)
        if new_hash != old_hash:
            reload_homepage()  # Trigger reload if the config file has changed

    except Exception as e:
        print(f"❌ Error updating config: {e}", flush=True)

def listen_for_container_events():
    """Listen for Docker container events and update config when new containers are added"""
    for event in client.events(decode=True):
        print(f"Event detected: {event}", flush=True)
        if event["Type"] == "container" and event["Action"] in ["start", "die", "destroy"]:
            print(f"🔔 Detected container event: {event['Action']} for {event['Actor']['Attributes']['name']}", flush=True)
            update_homepage_config(get_current_containers())

if __name__ == "__main__":
    print("Listening for Docker container events...", flush=True)
    listen_for_container_events()