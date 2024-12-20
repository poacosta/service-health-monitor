import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceType(Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"


@dataclass
class Service:
    name: str
    url: str
    type: ServiceType
    timeout: int = 30
    expected_status: int = 200
    custom_headers: Optional[Dict[str, str]] = None


class HealthChecker:
    def __init__(self, slack_webhook_url: str):
        self.slack_webhook_url = slack_webhook_url
        self.services: List[Service] = []

    def add_service(self, service: Service) -> None:
        self.services.append(service)

    async def check_service(self, service: Service) -> Dict:
        start_time = datetime.now()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        service.url,
                        timeout=service.timeout,
                        headers=service.custom_headers or {},
                        ssl=True
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    is_healthy = response.status == service.expected_status

                    return {
                        "name": service.name,
                        "type": service.type.value,
                        "status": "healthy" if is_healthy else "unhealthy",
                        "response_time": elapsed,
                        "status_code": response.status,
                        "timestamp": datetime.now().isoformat()
                    }

        except asyncio.TimeoutError:
            logger.error(f"Timeout while checking {service.name}")
            return self._create_error_result(service, "timeout")
        except Exception as e:
            logger.error(f"Error checking {service.name}: {str(e)}")
            return self._create_error_result(service, str(e))

    def _create_error_result(self, service: Service, error: str) -> Dict:
        return {
            "name": service.name,
            "type": service.type.value,
            "status": "unhealthy",
            "error": error,
            "status_code": None,
            "timestamp": datetime.now().isoformat()
        }

    async def notify_slack(self, results: List[Dict]) -> None:
        unhealthy_services = [r for r in results if r["status"] == "unhealthy"]

        if not unhealthy_services:
            return

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *Service Health Alert* - Environment: {os.environ.get('ENVIRONMENT', 'unknown')}"
                }
            }
        ]

        for service in unhealthy_services:
            block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{service['name']}* ({service['type']})\n"
                        f"Status: {service['status']}\n"
                        f"Status Code: {service['status_code']}\n"
                        f"Error: {service.get('error', 'N/A')}\n"
                        f"Time: {service['timestamp']}"
                    )
                }
            }
            blocks.append(block)

        payload = {"blocks": blocks}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.slack_webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack notification: {response.status}")
            except Exception as e:
                logger.error(f"Error sending Slack notification: {str(e)}")

    async def check_all_services(self) -> List[Dict]:
        tasks = [self.check_service(service) for service in self.services]
        results = await asyncio.gather(*tasks)
        await self.notify_slack(results)
        return results


def get_services() -> List[Service]:
    """Load service configurations from environment variables."""
    services = []

    # Parse JSON configuration from environment variable
    services_config = json.loads(os.environ.get('SERVICES_CONFIG', '[]'))

    for config in services_config:
        services.append(Service(
            name=config['name'],
            url=config['url'],
            type=ServiceType(config['type']),
            timeout=config.get('timeout', 30),
            expected_status=config.get('expected_status', 200),
            custom_headers=config.get('custom_headers')
        ))

    return services


async def run_health_check():
    checker = HealthChecker(os.environ['SLACK_WEBHOOK_URL'])

    # Load services from configuration
    services = get_services()
    for service in services:
        checker.add_service(service)

    return await checker.check_all_services()


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    try:
        # Create new event loop for Lambda environment
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        results = loop.run_until_complete(run_health_check())

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Health check completed',
                'results': results
            })
        }

    except Exception as e:
        logger.error(f"Error in lambda execution: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
