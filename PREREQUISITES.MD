# Service Health Monitor: Prerequisites Guide 🚀

Let's get real about setting up your development environment. Having been through this process countless times (and
hitting every possible roadblock), I've compiled this guide to save you from the same head-scratching moments I
encountered.

## Essential Components Overview

Quick reality check — here's what you'll need:

- AWS Account (your cloud playground)
- Terraform (your infrastructure's blueprint maker)
- Python 3.9 (our Lambda's language of choice)
- Slack Workspace (where the alerts live)
- Various CLI tools (because GUIs are so 2010)

## Detailed Setup Guide 🛠️

### 1. AWS Account Setup 🌩️

You'll need an AWS account with:

- An IAM user with programmatic access
- Appropriate permissions (Lambda, CloudWatch, IAM)

Quick setup:

```bash
# Install AWS CLI
brew install awscli  # Mac
# or
apt-get install awscli  # Linux

# Configure AWS CLI
aws configure
# You'll need to enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Output format (json recommended)
```

**Official Guide**: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html

Pro tip: Create a dedicated IAM user for this project. Your future self will thank you when managing permissions!

### 2. Terraform Installation 🏗️

Terraform is our infrastructure-as-code buddy.

Here's how to get it: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli

Remember: Terraform state files are like your infrastructure's diary — keep them safe and never commit them to version
control!

### 3. Python Environment 🐍

The Lambda function needs Python 3.9:

```bash
# Check Python version
python3 --version

# Create virtual environment
python3.9 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
```

**Official Guide**: https://docs.python.org/3/library/venv.html

### 4. Slack Webhook Setup 💬

This is where the magic of notifications happens.

Here's a quick guide to get your webhook URL: https://api.slack.com/messaging/webhooks

Pro tip: Create a dedicated channel like #service-health for these notifications. Your team's #general channel will
thank you!

### 5. Local Development Tools 🛠️

Some quality-of-life tools:

```bash
# Install pip if you haven't
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py

# Install development dependencies
pip install black isort pylint  # Code formatting and linting
```

**Guide**: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/

### 6. Lambda Deployment Package 📦

Ah, the famous `dist` folder - let's talk about why it's crucial and how to set it up properly.

#### Why Do We Need This? 🤔

Here's the thing about AWS Lambda: it's like packing for a trip where you need to bring everything you might need
because there's no convenience store at your destination. Your Lambda function needs all its dependencies bundled
together in a neat little package.

The `dist` folder is where this magic happens. Think of it as your function's suitcase - it needs to contain:

- Your Lambda function code
- All the Python packages it depends on
- Any additional assets or configurations

#### Creating the Deployment Package 🎒

Here's the step-by-step process to create your Lambda's travel kit:

```bash
# 1. Create the dist directory
mkdir -p dist

# 2. Install dependencies directly into dist
pip install -r requirements.txt -t dist/
# What this does:
# -r requirements.txt: Read dependencies from this file
# -t dist/: Install them in the dist directory instead of globally

# 3. Copy your Lambda function
cp src/lambda_function.py dist/

# 4. Create the zip file (from the root directory)
cd dist && zip -r lambda_function.zip . && cd ..
```

ℹ️ These commands are also available in [reset-dist.sh](utils/reset-dist.sh) at [utils](utils) folder for convenience.

#### The Anatomy of Your dist Folder 🔍

After running these commands, your `dist` folder should look something like this:

```
dist/
├── aiohttp/                 # Your HTTP client library
├── multidict/              # aiohttp dependency
├── yarl/                   # Another aiohttp dependency
├── lambda_function.py      # Your actual function
└── lambda_function.zip     # The final package for AWS
```

#### Common Gotchas and Pro Tips 🎯

1. **Size Matters**: AWS Lambda has a deployment package size limit
    - Uncompressed: 250 MB
    - Compressed: 50 MB
      Keep an eye on your dependencies!

2. **Clean Before You Pack**: Always create a fresh dist folder
   ```bash
   rm -rf dist/* && mkdir -p dist
   ```

3. **Dependency Drama**: Sometimes pip installs extra stuff you don't need
   ```bash
   # Optional: Remove unnecessary files
   find dist/ -type d -name "__pycache__" -exec rm -rf {} +
   ```

4. **Platform Compatibility**: If you're developing on macOS but deploying to Lambda (Linux)
   ```bash
   # Use --platform to ensure Linux compatibility
   pip install --platform manylinux2014_x86_64 --target dist/ --implementation cp --python-version 3.9 --only-binary=:all: -r requirements.txt
   ```

Remember: A well-organized deployment package is like a well-packed suitcase — it makes your Lambda's life much easier!
🧳

## Common Pitfalls and Their Solutions 🎯

Because I've probably hit every one of these:

1. **AWS Credentials Drama**
    - Symptoms: "Unable to locate credentials"
    - Fix: `aws configure` is your friend
    - Double-check with: `aws sts get-caller-identity`

2. **Terraform State Confusion**
    - Symptom: "State file not found"
    - Fix: Initialize with `terraform init`
    - Pro tip: Use remote state storage for team environments

3. **Python Version Mismatch**
    - Symptom: "Runtime.ImportError"
    - Fix: Stick to Python 3.9
    - Verify with: `python --version`

4. **Deployment Package Size**
    - Symptom: "Deployment package too large"
    - Fix: Clean unnecessary files
   ```bash
   find dist/ -type d -name "__pycache__" -exec rm -rf {} +
   ```

## Quick Start Verification ✅

Run this checklist before proceeding:

```bash
# AWS
aws sts get-caller-identity  # Should show your account info

# Terraform
terraform -v  # Should show version info

# Python
python3.9 -m pip freeze  # Should show your dependencies

# Deployment Package
ls -lh dist/lambda_function.zip  # Should be under 50MB
```

## What's Next? 🎬

With all prerequisites satisfied, head back to the main [README.md](README.md) to start building your monitoring system. Remember, a
solid foundation makes for a stable house... or in this case, a reliable monitoring system!
