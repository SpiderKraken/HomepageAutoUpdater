import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import monitor_containers
import yaml

class TestMonitorContainers(unittest.TestCase):

    @patch('monitor_containers.client')
    def test_get_current_containers(self, mock_client):
        # Mock the Docker client
        mock_container = MagicMock()
        mock_container.name = "test_container"
        mock_container.attrs = {
            "Config": {"Image": "test_image"},
            "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "8080"}]}}
        }
        mock_client.containers.list.return_value = [mock_container]

        # Call the function
        container_data = monitor_containers.get_current_containers()

        # Check the results
        self.assertIn("test_container", container_data)
        self.assertEqual(container_data["test_container"]["image"], "test_image")
        self.assertEqual(container_data["test_container"]["port"], "8080")

    @patch('monitor_containers.requests.post')
    def test_reload_homepage(self, mock_post):
        # Mock the requests.post method
        mock_post.return_value.status_code = 200

        # Call the function
        monitor_containers.reload_homepage()

        # Check that the post request was made
        mock_post.assert_called_once_with(monitor_containers.HOMEPAGE_URL)

    @patch('builtins.open', new_callable=mock_open, read_data="containers:\n  test_service: {}")
    @patch('monitor_containers.yaml.safe_load')
    @patch('monitor_containers.yaml.safe_dump')
    @patch('os.access', return_value=True)
    def test_update_yaml(self, mock_os_access, mock_safe_dump, mock_safe_load, mock_open):
        # Mock the yaml.safe_load method
        mock_safe_load.return_value = {"containers": [{"name": "test_service"}]}

        # Mock container data
        container_data = {
            "test_container": {
                "image": "test_image",
                "port": "8080",
                "category": "media"
            }
        }

        # Simulate write failure on the first call
        mock_open_instance = mock_open(read_data="containers:\n  test_service: {}")
        mock_open.side_effect = [mock_open_instance.return_value,
                                 Exception("Simulated write failure"),
                                 mock_open_instance.return_value]

        # Call the function
        monitor_containers.update_yaml(container_data)

        # Check that the file was opened and written to
        mock_open_instance.assert_any_call(monitor_containers.HOMEPAGE_CONFIG_PATH, 'r')
        mock_open_instance.assert_any_call(monitor_containers.HOMEPAGE_CONFIG_PATH, 'w')
        
        # Get the actual file handle used in the 'w' call
        handle = mock_open_instance()
        handle().write.assert_called()  # Ensure write was called on the file handle
        mock_safe_dump.assert_called_with({"containers": [{"name": "test_service"}, {"name": "test_container", "image": "test_image", "port": "8080", "category": "media"}]}, handle())

if __name__ == '__main__':
    unittest.main()