# Service Health Monitor

Ever had that moment when your production services decided to take an unannounced vacation?
Yeah, me too.
That's why I
built this automated health monitoring system that keeps tabs on your services and sends Slack notifications when things
go sideways.
Think of it as your infrastructure's personal health assistant.

## 🎯 Prerequisites

Before diving in, make sure you have all the necessary components set up.
Check out [PREREQUISITES.md](PREREQUISITES.MD) for a detailed setup guide.

### Quick Sanity Check ✅

Before proceeding, verify:

- [ ] AWS CLI configured (`aws sts get-caller-identity`)
- [ ] Terraform installed (`terraform -v`)
- [ ] Python 3.9 available (`python3.9 --version`)
- [ ] Slack webhook URL obtained
- [ ] Virtual environment activated
- [ ] `dist/` directory with all necessary files

If any of these are missing, check the detailed sections above. Trust me, it's worth getting these, right from the
start!

## Features

- **Async Health Checks**: Because waiting is so 2010
- **Slack Integration**: Get notifications that actually look good (and are useful!)
- **AWS Lambda Ready**: Serverless, because who wants to manage servers for monitoring servers?
- **Infrastructure as Code**: Everything in Terraform, because we're professionals here
- **Configurable Monitoring**: Customize everything from timeouts to headers
- **Multi-Service Support**: Monitor both frontend and backend services in one go

## 🚀 Quick Start

1. Clone this repo:

```bash
git clone https://github.com/poacosta/service-health-monitor
cd service-health-monitor
```

2. Set up your Python environment:

```bash
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

3. Create your `terraform.tfvars`:

```hcl
project_name      = "my-awesome-project"
environment       = "production"
slack_webhook_url = "https://hooks.slack.com/services/your/webhook/url"
services_config = [
  {
    name            = "Backend API"
    url             = "https://api.example.com/health"
    type            = "backend"
    timeout         = 30
    expected_status = 200
    custom_headers = {
      "Authorization" = "Bearer your-token-if-needed"
    }
  },
  {
    name            = "Frontend App"
    url             = "https://app.example.com"
    type            = "frontend"
    timeout         = 30
    expected_status = [200, 429, 403]
  }
]
```

4. Deploy to AWS:

```bash
cd terraform
terraform init -upgrade
terraform plan
terraform apply
```

## 🎯 Use Cases

- **Microservices Monitoring**: Keep track of your distributed services
- **Frontend Health**: Monitor your user-facing applications
- **API Availability**: Ensure your APIs are responding correctly
- **Custom Health Checks**: Add custom headers for authenticated endpoints

## 🔧 Configuration

### Service Configuration

Each service in your `terraform.tfvars` can have:

- `name`: Service identifier
- `url`: Health check endpoint
- `type`: "backend" or "frontend"
- `timeout`: Request timeout in seconds (default: 30)
- `expected_status`: Expected HTTP statuses (default: 200)
- `custom_headers`: Additional HTTP headers

### Schedule Configuration

Modify the check frequency in `terraform.tfvars`:

```hcl
schedule_expression = "rate(5 minutes)"  # Default
# OR
schedule_expression = "cron(0/15 * * * ? *)"  # Every 15 minutes
```

### Config Example

📓 [terraform.tfvars.example](terraform/terraform.tfvars.example)

## 🏗 Architecture

```
┌─────────────┐     ┌──────────┐     ┌────────────┐
│ EventBridge │ ──▶ │  Lambda  │ ──▶ │  Services  │
└─────────────┘     └──────────┘     └────────────┘
                         │
                         ▼
                    ┌─────────┐
                    │  Slack  │
                    └─────────┘
```

## 📈 Future Improvements

- [ ] Add metrics export to CloudWatch
- [ ] Implement retry mechanisms with exponential backoff
- [ ] Add support for custom health check logic
- [ ] Create a dashboard for historical uptime data
- [ ] Add support for multiple notification channels

## 🤝 Contributing

Feel free to dive in! [Open an issue](https://github.com/poacosta/service-health-monitor/issues/new) or submit PRs.

### Development Setup

1. Fork the Repository
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The async Python community for making non-blocking requests a breeze
- Terraform for making infrastructure manageable
- Coffee ☕ for making everything possible

## 🔐 Security

Please ensure you never commit sensitive information like tokens or webhook URLs. Use environment variables or AWS
Secrets Manager for production deployments.

## ✨ About

Built with love for DevOps engineers who want to sleep better at night.
Because your services should notify you before your users do.
