# Clean previous dist
rm -rf dist/*

# Create fresh dist directory
mkdir -p dist

# Install all dependencies
pip install -r requirements.txt -t dist/

# Copy lambda function
cp src/lambda_function.py dist/

# Create zip package (from the dist directory)
cd dist && zip -r lambda_function.zip . && cd ..
