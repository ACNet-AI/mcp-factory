"""FastMCP-Factory Basic Performance Test Module.

This module contains performance tests for FastMCP-Factory, used to measure performance characteristics of key operations.
"""

import os
import tempfile
import time
from unittest.mock import patch

import pytest
import yaml

from mcp_factory import FastMCPFactory


class TestFactoryPerformance:
    """Test performance characteristics of FastMCPFactory."""

    def test_server_creation_performance(self) -> None:
        """Measure server creation performance."""
        factory = FastMCPFactory()

        # Create basic server configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            server_config = {
                "server": {
                    "name": "perf-test",
                    "instructions": "Performance test server",
                    "host": "localhost",
                    "port": 8080,
                }
            }
            yaml_content = yaml.dump(server_config)
            temp_file.write(yaml_content.encode("utf-8"))
            base_config_path = temp_file.name

        # Create multiple temporary configuration files
        config_files = []
        for i in range(13):  # 3 for warmup + 10 for performance testing
            # Copy basic configuration to new file, modify server name
            with open(base_config_path) as f:
                config_data = yaml.safe_load(f)

            # Update server name
            if i < 3:
                config_data["server"]["name"] = f"warmup-{i}"
            else:
                config_data["server"]["name"] = f"perf-server-{i - 3}"

            # Save modified configuration
            config_path = f"{base_config_path}-{i}"
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            config_files.append(config_path)

        try:
            # Avoid actually starting servers
            with patch("fastmcp.FastMCP.run"):
                # Warmup
                for i in range(3):
                    # Create but don't save variable reference, warmup phase
                    factory.create_managed_server(config_path=config_files[i])

                # Clear warmup servers
                factory._servers.clear()

                # Execute performance test
                start_time = time.time()
                server_count = 10

                for i in range(server_count):
                    # Create but don't save variable reference, since we only care about performance, not return values
                    factory.create_managed_server(config_path=config_files[i + 3])

                end_time = time.time()
                total_time = end_time - start_time

                # Calculate average creation time
                avg_creation_time = total_time / server_count

                # Validate performance metrics (set more lenient thresholds)
                assert avg_creation_time < 0.2, (
                    f"Average server creation time too long: {avg_creation_time:.4f} seconds"
                )

                # Output performance metrics
                print("\nPerformance Test Results:")
                print(f"Total creation time: {total_time:.4f} seconds")
                print(f"Average creation time: {avg_creation_time:.4f} seconds")
                print(f"Creations per second: {server_count / total_time:.1f} per second")
        finally:
            # Clean up all temporary files
            for file_path in config_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            if os.path.exists(base_config_path):
                os.unlink(base_config_path)


class TestConfigPerformance:
    """Test performance characteristics of configuration processing."""

    @pytest.mark.parametrize("server_count", [1, 5, 10])
    def test_config_reload_performance(self, server_count: int, temp_config_file: str) -> None:
        """Measure configuration reload performance as server count increases."""
        factory = FastMCPFactory()

        # Create multiple servers
        servers = []
        for i in range(server_count):
            server = factory.create_managed_server(config_path=temp_config_file)
            servers.append(server)

        # Measure time to reload configuration for all servers
        start_time = time.time()

        for server in servers:
            server.reload_config(config_path=temp_config_file)

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate average reload time
        avg_reload_time = total_time / server_count

        # Validate performance metrics (set more lenient thresholds)
        assert avg_reload_time < 0.5, (
            f"Average configuration reload time too long: {avg_reload_time:.4f} seconds"
        )

        # Output performance metrics
        print(f"\nConfiguration Reload Performance Results ({server_count} servers):")
        print(f"Total reload time: {total_time:.4f} seconds")
        print(f"Average reload time per server: {avg_reload_time:.4f} seconds")


# More performance test classes can be added if needed
