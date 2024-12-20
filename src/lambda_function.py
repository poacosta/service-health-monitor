import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceType(Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    reset_timeout: int = 60  # seconds
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = datetime.now()
        if self.failures >= self.failure_threshold:
            self.is_open = True

    def record_success(self) -> None:
        self.failures = 0
        self.is_open = False
        self.last_failure_time = None

    def can_try(self) -> bool:
        if not self.is_open:
            return True
        if (datetime.now() - self.last_failure_time) > timedelta(seconds=self.reset_timeout):
            self.is_open = False
            self.failures = 0
            return True
        return False


@dataclass
class ServiceMetrics:
    total_checks: int = 0
    total_failures: int = 0
    avg_response_time: float = 0.0
    last_check_time: Optional[datetime] = None
    min_response_time: float = float('inf')
    max_response_time: float = 0.0


@dataclass
class Service:
    name: str
    url: str
    type: ServiceType
    timeout: int = 30
    expected_status: int = 200
    custom_headers: Optional[Dict[str, str]] = None
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds


class HealthChecker:
    def __init__(self, slack_webhook_url: str):
        self.slack_webhook_url = slack_webhook_url
        self.services: List[Service] = []
        self.metrics: Dict[str, ServiceMetrics] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    def add_service(self, service: Service) -> None:
        self.services.append(service)
        if service.name not in self.metrics:
            self.metrics[service.name] = ServiceMetrics()

    def update_metrics(self, service_name: str, response_time: float, is_failure: bool) -> None:
        metrics = self.metrics[service_name]
        metrics.total_checks += 1
        if is_failure:
            metrics.total_failures += 1

        metrics.min_response_time = min(metrics.min_response_time, response_time)
        metrics.max_response_time = max(metrics.max_response_time, response_time)
        metrics.avg_response_time = (
                (metrics.avg_response_time * (metrics.total_checks - 1) + response_time)
                / metrics.total_checks
        )
        metrics.last_check_time = datetime.now()

    async def check_service(self, service: Service) -> Dict:
        if not service.circuit_breaker.can_try():
            return {
                "name": service.name,
                "type": service.type.value,
                "status": "circuit_open",
                "error": "Circuit breaker is open",
                "timestamp": datetime.now().isoformat()
            }

        start_time = datetime.now()

        for attempt in range(service.retry_attempts):
            try:
                async with self._session.get(
                        service.url,
                        timeout=service.timeout,
                        headers=service.custom_headers or {},
                        ssl=True
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    is_healthy = response.status == service.expected_status

                    if is_healthy:
                        service.circuit_breaker.record_success()
                    else:
                        service.circuit_breaker.record_failure()

                    self.update_metrics(service.name, elapsed, not is_healthy)

                    return {
                        "name": service.name,
                        "type": service.type.value,
                        "status": "healthy" if is_healthy else "unhealthy",
                        "response_time": elapsed,
                        "status_code": response.status,
                        "expected_status": service.expected_status,
                        "attempt": attempt + 1,
                        "timestamp": datetime.now().isoformat()
                    }

            except asyncio.TimeoutError:
                logger.error(f"Timeout while checking {service.name} (attempt {attempt + 1})")
                if attempt < service.retry_attempts - 1:
                    await asyncio.sleep(service.retry_delay * (attempt + 1))
                    continue
                return self._create_error_result(service, "timeout")

            except Exception as e:
                logger.error(f"Error checking {service.name}: {str(e)} (attempt {attempt + 1})")
                if attempt < service.retry_attempts - 1:
                    await asyncio.sleep(service.retry_delay * (attempt + 1))
                    continue
                return self._create_error_result(service, str(e))

    def _create_error_result(self, service: Service, error: str) -> Dict:
        service.circuit_breaker.record_failure()
        self.update_metrics(service.name, 0.0, True)

        return {
            "name": service.name,
            "type": service.type.value,
            "status": "unhealthy",
            "error": error,
            "status_code": None,
            "expected_status": service.expected_status,
            "timestamp": datetime.now().isoformat()
        }

    async def notify_slack(self, results: List[Dict]) -> None:
        unhealthy_services = [
            r for r in results
            if r["status"] in ("unhealthy", "circuit_open") and (
                    r.get("status_code") != r.get("expected_status") or
                    "error" in r
            )
        ]

        if not unhealthy_services:
            return

        services_by_type = {}
        for service in unhealthy_services:
            service_type = service["type"]
            if service_type not in services_by_type:
                services_by_type[service_type] = []
            services_by_type[service_type].append(service)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Service Health Alert - {os.environ.get('ENVIRONMENT', 'unknown')}"
                }
            }
        ]

        for service_type, services in services_by_type.items():
            blocks.extend([
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{service_type.upper()} Services*"
                    }
                }
            ])

            for service in services:
                metrics = self.metrics.get(service['name'])
                failure_rate = (
                    (metrics.total_failures / metrics.total_checks * 100)
                    if metrics and metrics.total_checks > 0
                    else 0
                )

                block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{service['name']}*\n"
                            f"• Status: {service['status']}\n"
                            f"• Status Code: {service.get('status_code', 'N/A')} "
                            f"(Expected: {service.get('expected_status', 'N/A')})\n"
                            f"• Error: {service.get('error', 'N/A')}\n"
                            f"• Response Time: {service.get('response_time', 'N/A')}s\n"
                            f"• Failure Rate: {failure_rate:.1f}%\n"
                            f"• Time: {service['timestamp']}"
                        )
                    }
                }

                if service['status'] == 'circuit_open':
                    block["accessory"] = {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reset Circuit"
                        },
                        "value": f"reset_circuit_{service['name']}"
                    }

                blocks.append(block)

        blocks.extend([
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*Total Unhealthy Services:* {len(unhealthy_services)} | "
                            f"*Environment:* {os.environ.get('ENVIRONMENT', 'unknown')} | "
                            f"*Alert Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        )
                    }
                ]
            }
        ])

        payload = {"blocks": blocks}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.slack_webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack notification: {response.status}")
                        await response.text()
            except Exception as e:
                logger.error(f"Error sending Slack notification: {str(e)}")

    async def check_all_services(self) -> List[Dict]:
        async with self:
            tasks = [self.check_service(service) for service in self.services]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Service check failed: {str(result)}")
                    continue
                processed_results.append(result)

            await self.notify_slack(processed_results)
            return processed_results

    def get_metrics_report(self) -> Dict:
        return {
            name: {
                "total_checks": metrics.total_checks,
                "total_failures": metrics.total_failures,
                "failure_rate": (metrics.total_failures / metrics.total_checks) if metrics.total_checks > 0 else 0,
                "avg_response_time": metrics.avg_response_time,
                "min_response_time": metrics.min_response_time,
                "max_response_time": metrics.max_response_time,
                "last_check_time": metrics.last_check_time.isoformat() if metrics.last_check_time else None
            }
            for name, metrics in self.metrics.items()
        }


def get_services() -> List[Service]:
    """Load service configurations from environment variables with validation."""
    try:
        services_config = json.loads(os.environ.get('SERVICES_CONFIG', '[]'))
        if not isinstance(services_config, list):
            raise ValueError("SERVICES_CONFIG must be a JSON array")

        services = []
        for idx, config in enumerate(services_config):
            # Validate required fields
            required_fields = ['name', 'url', 'type']
            missing_fields = [_field for _field in required_fields if _field not in config]
            if missing_fields:
                raise ValueError(f"Service at index {idx} missing required fields: {missing_fields}")

            # URL validation
            if not config['url'].startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format for service {config['name']}")

            # Timeout validation
            try:
                timeout = int(config.get('timeout', 30) or 30)
                if timeout <= 0:
                    raise ValueError(f"Timeout value must be positive for service {config['name']}")
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid timeout value for service {config['name']}. "
                    f"Expected a positive number, got: {config.get('timeout')}"
                )

            services.append(Service(
                name=config['name'],
                url=config['url'],
                type=ServiceType(config['type']),
                timeout=timeout,
                expected_status=config.get('expected_status', 200),
                custom_headers=config.get('custom_headers')
            ))

        return services

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in SERVICES_CONFIG: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Configuration error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error in configuration: {str(e)}")


async def run_health_check():
    checker = HealthChecker(os.environ['SLACK_WEBHOOK_URL'])

    services = get_services()
    for service in services:
        checker.add_service(service)

    return await checker.check_all_services()


def lambda_handler(event, lambda_context):
    """AWS Lambda entry point."""
    try:
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
