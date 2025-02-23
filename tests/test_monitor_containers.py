import sys
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
import yaml

# Adjust the import path to correctly reference the monitor_containers module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import monitor_containers
from monitor_containers import (
    ContainerData,
    update_homepage_config,
    HOMEPAGE_CONFIG_PATH,
    HOMEPAGE_URL,
)

@pytest.fixture
def sample_containers():
    return [
        ContainerData(name="container1", image="image1", category="category1", port="8080"),
        ContainerData(name="container2", image="image2", category="category2", port="9090"),
    ]

@patch('monitor_containers.get_docker_client')
def test_get_current_containers(mock_get_docker_client, sample_containers):
    # Mock the Docker client
    mock_container = MagicMock()
    mock_container.name = "test_container"
    mock_container.attrs = {
        "Config": {"Image": "test_image"},
        "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "8080"}]}}
    }
    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_container]
    mock_get_docker_client.return_value = mock_client

    # Call the function
    container_data = monitor_containers.get_current_containers()

    # Check the results
    assert len(container_data) == 1
    assert container_data[0].name == "test_container"
    assert container_data[0].image == "test_image"
    assert container_data[0].port == "8080"

@patch('monitor_containers.requests.post')
def test_reload_homepage(mock_post):
    # Mock the requests.post method
    mock_post.return_value.status_code = 200

    # Call the function
    monitor_containers.reload_homepage()

    # Check that the post request was made
    mock_post.assert_called_once_with(HOMEPAGE_URL)

@pytest.mark.parametrize("file_exists", [True, False])
def test_update_homepage_config(tmpdir, file_exists, sample_containers):
    # Create a temporary file for testing
    temp_file = tmpdir.join("services.yaml")
    temp_file_path = str(temp_file)

    # Mock container data
    container_data = [
        ContainerData(name="new_container", image="new_image", port="7070", category="new_category")
    ]

    # Simulate file existence with realistic data
    if file_exists:
        temp_file.write(yaml.safe_dump({
            "containers": [
                {"name": "existing_service", "image": "existing_image", "port": "9090", "category": "existing_category"}
            ]
        }))
    else:
        temp_file.ensure()

    # Update the HOMEPAGE_CONFIG_PATH to use the temporary file
    with patch('monitor_containers.HOMEPAGE_CONFIG_PATH', temp_file_path):
        # Call the function
        try:
            update_homepage_config(container_data)
        except FileNotFoundError:
            if not file_exists:
                pass  # Expected behavior
            else:
                raise

    # Check that the file was opened and written to
    if file_exists:
        expected_content = yaml.safe_dump({
            "containers": [
                {"name": "existing_service", "image": "existing_image", "port": "9090", "category": "existing_category"},
                {"name": "new_container", "image": "new_image", "port": "7070", "category": "new_category"}
            ]
        })
        actual_content = temp_file.read()
        print("Expected content:", expected_content)
        print("Actual content:", actual_content)
        assert actual_content == expected_content

if __name__ == '__main__':
    pytest.main()