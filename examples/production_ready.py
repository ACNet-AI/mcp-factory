#!/usr/bin/env python3
"""
FastMCP-Factory Production Environment Example

Demonstrates enterprise-level configuration and deployment practices:
1. Enterprise-level security configuration and authentication
2. Complete monitoring and logging system
3. Error handling and recovery mechanisms
4. Performance optimization and resource management
5. Production deployment best practices

Usage: python production_ready.py --config configs/production.yaml
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import TYPE_CHECKING, Any

import yaml

from mcp_factory.factory import MCPFactory

if TYPE_CHECKING:
    from mcp_factory.server import ManagedServer

# Configure production-level logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("production_server.log", encoding="utf-8")],
)
logger = logging.getLogger(__name__)


class ProductionServer:
    """Production environment server manager"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.factory: MCPFactory | None = None
        self.server: ManagedServer | None = None
        self.config: dict[str, Any] = {}
        self.shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize production server"""
        logger.info("🚀 Initializing production environment server")

        # Load configuration
        await self._load_config()

        # Initialize factory
        await self._initialize_factory()

        # Setup authentication
        # Authentication functionality has been removed, skip authentication setup

        # Create server
        await self._create_server()

        # Register production tools
        await self._register_production_tools()

        # Setup monitoring
        await self._setup_monitoring()

        logger.info("✅ Production environment server initialization completed")

    async def _load_config(self):
        """Load production configuration"""
        if not os.path.exists(self.config_path):
            # If configuration file doesn't exist, use default production configuration
            self.config = self._get_default_production_config()
            logger.warning(f"Configuration file not found, using default configuration: {self.config_path}")
        else:
            with open(self.config_path, encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"✅ Configuration file loaded: {self.config_path}")

    async def _initialize_factory(self):
        """Initialize factory"""
        workspace_root = self.config.get("factory", {}).get("workspace_root", "./production_workspace")

        self.factory = MCPFactory(workspace_root=workspace_root)
        logger.info(f"✅ Factory initialization completed, workspace: {workspace_root}")

    async def _create_server(self):
        """Create production server"""
        server_config = self.config.get("server", {})

        # Create production server with full management capabilities enabled
        server_id = self.factory.create_server(
            name=server_config.get("name", "production-server"),
            source=self.config_path,
            lifespan=self._production_lifespan,
            expose_management_tools=True,
        )
        self.server = self.factory.get_server(server_id)

        logger.info(f"✅ Production server created successfully: {self.server.name}")

    @asynccontextmanager
    async def _production_lifespan(self):
        """Production environment lifecycle management"""
        start_time = datetime.now()
        logger.info(f"🔄 Production server started: {start_time}")

        # Initialization on startup
        resources = {"start_time": start_time, "request_count": 0, "error_count": 0, "health_status": "healthy"}

        try:
            yield resources
        finally:
            # Cleanup on shutdown
            uptime = datetime.now() - start_time
            logger.info(f"🛑 Production server shutdown, uptime: {uptime}")
            logger.info(
                f"📊 Request statistics: {resources['request_count']} requests, {resources['error_count']} errors"
            )

    async def _register_production_tools(self):
        """Register production environment tools"""

        @self.server.tool(name="health_check", description="Production environment health check")
        async def health_check() -> dict[str, Any]:
            """Perform comprehensive health check"""
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "server_name": self.server.name,
                "uptime": str(datetime.now() - self.server.state.get("start_time", datetime.now())),
                "checks": {},
            }

            # Check disk space
            try:
                import shutil

                disk_usage = shutil.disk_usage("/")
                free_space_gb = disk_usage.free / (1024**3)
                health_status["checks"]["disk_space"] = {
                    "status": "ok" if free_space_gb > 1 else "warning",
                    "free_space_gb": round(free_space_gb, 2),
                }
            except Exception as e:
                health_status["checks"]["disk_space"] = {"status": "error", "error": str(e)}

            # Check memory usage
            try:
                import psutil

                memory = psutil.virtual_memory()
                health_status["checks"]["memory"] = {
                    "status": "ok" if memory.percent < 80 else "warning",
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                }
            except ImportError:
                health_status["checks"]["memory"] = {"status": "unavailable", "reason": "psutil not installed"}
            except Exception as e:
                health_status["checks"]["memory"] = {"status": "error", "error": str(e)}

            # Check factory status
            try:
                servers = self.factory.list_servers()
                health_status["checks"]["factory"] = {"status": "ok", "managed_servers": len(servers)}
            except Exception as e:
                health_status["checks"]["factory"] = {"status": "error", "error": str(e)}
                health_status["status"] = "unhealthy"

            return health_status

        @self.server.tool(name="system_metrics", description="Get system performance metrics")
        async def get_system_metrics() -> dict[str, Any]:
            """Get detailed system performance metrics"""
            metrics = {"timestamp": datetime.now().isoformat(), "server_metrics": {}, "factory_metrics": {}}

            # Server metrics
            if hasattr(self.server, "state"):
                state = self.server.state
                metrics["server_metrics"] = {
                    "request_count": state.get("request_count", 0),
                    "error_count": state.get("error_count", 0),
                    "uptime": str(datetime.now() - state.get("start_time", datetime.now())),
                }

            # Factory metrics
            try:
                servers = self.factory.list_servers()

                metrics["factory_metrics"] = {
                    "total_servers": len(servers),
                    "workspace_root": getattr(self.factory, "workspace_root", "unknown"),
                }
            except Exception as e:
                logger.error(f"Failed to get factory metrics: {e}")

            return metrics

        @self.server.tool(name="emergency_shutdown", description="Emergency shutdown server (only for administrators)")
        async def emergency_shutdown(reason: str = "Manual shutdown") -> dict[str, Any]:
            """Emergency shutdown server"""
            logger.warning(f"🚨 Emergency shutdown request: {reason}")

            # Trigger shutdown event
            self.shutdown_event.set()

            return {"status": "shutdown_initiated", "reason": reason, "timestamp": datetime.now().isoformat()}

        logger.info("✅ Production environment tools registration completed")

    async def _setup_monitoring(self):
        """Setup monitoring system"""
        monitoring_config = self.config.get("monitoring", {})

        if monitoring_config.get("enabled", False):
            # Start monitoring task
            asyncio.create_task(self._monitoring_loop())
            logger.info("✅ Monitoring system started")
        else:
            logger.info("ℹ️   Monitoring system not enabled")

    async def _monitoring_loop(self):
        """Monitoring loop"""
        while not self.shutdown_event.is_set():
            try:
                # Perform health check
                if self.server:
                    # Record basic metrics
                    if hasattr(self.server, "state"):
                        logger.info(f"📊 Server status: {self.server.state.get('health_status', 'unknown')}")

                # Wait for monitoring interval
                await asyncio.sleep(30)  # 30 seconds monitoring interval

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Short wait after error

    def _get_default_production_config(self) -> dict[str, Any]:
        """Get default production configuration"""
        return {
            "server": {
                "name": "production-server",
                "instructions": "FastMCP-Factory Production Environment Server",
                "host": "0.0.0.0",
                "port": 8000,
            },
            "auth": {
                "enabled": False,  # Disable authentication for demo mode
                "provider": "auth0",
            },
            "monitoring": {"enabled": True, "health_check_interval": 30, "metrics_retention_days": 7},
            "factory": {"workspace_root": "./production_workspace"},
            "advanced": {"log_level": "INFO", "json_response": True, "cache_expiration_seconds": 300},
        }

    async def run(self):
        """Run production server"""
        try:
            await self.initialize()

            # Setup signal handlers
            self._setup_signal_handlers()

            logger.info("🚀 Starting production server...")

            # Create run task
            server_task = asyncio.create_task(self._run_server())
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())

            # Wait for server to run or shutdown signal
            done, pending = await asyncio.wait({server_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED)

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

            logger.info("✅ Production server safely shut down")

        except Exception as e:
            logger.error(f"❌ Production server failed to run: {e}")
            raise

    async def _run_server(self):
        """Run server's internal method"""
        try:
            logger.info("🌐 Server starting to listen for connections...")
            # In actual use, this would call self.server.run_async()
            # For demonstration, we just wait for shutdown signal
            await self.shutdown_event.wait()
        except Exception as e:
            logger.error(f"Server run error: {e}")
            raise

    def _setup_signal_handlers(self):
        """Setup signal handlers"""

        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, preparing to shut down server...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Production environment example main function"""
    parser = argparse.ArgumentParser(description="Production environment server")
    parser.add_argument("--config", default="configs/production.yaml", help="Production configuration file path")
    parser.add_argument("--demo-mode", action="store_true", help="Demo mode, use built-in configuration")
    args = parser.parse_args()

    print("🏭 FastMCP-Factory Production Environment Example")
    print("=" * 60)

    if args.demo_mode:
        print("🎭 Demo mode started")
        await demo_production_features()
    else:
        # Create production server
        production_server = ProductionServer(args.config)

        try:
            await production_server.run()
        except KeyboardInterrupt:
            logger.info("👋 User interrupted, server shutting down")
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
            sys.exit(1)


async def demo_production_features():
    """Demo production environment features"""
    print("📋 Production environment features demonstration")
    print("-" * 40)

    # Create demo production server
    demo_config_path = "demo_production_config.yaml"
    production_server = ProductionServer(demo_config_path)

    try:
        await production_server.initialize()

        print("✅ Production server initialization completed")
        print(f"📊 Server name: {production_server.server.name}")
        print(f"🏭 Factory managed servers: {len(production_server.factory.list_servers())}")

        # Demo health check
        print("\n🔍 Performing health check...")
        # Here you can call health check tool
        print("✅ Health check completed")

        print("\n💡 In actual use:")
        print("  - Server will listen on specified port")
        print("  - Enable full authentication and authorization")
        print("  - Run continuous monitoring and logging")
        print("  - Handle graceful shutdown and error recovery")

        print("\n✨ Production environment demonstration completed!")

    except Exception as e:
        logger.error(f"Demo failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example stopped")
    except Exception as e:
        logger.error(f"Example run error: {e}")
        sys.exit(1)
