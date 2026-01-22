#!/bin/bash
# Startup diagnostic script for Wingman

echo "======================================================================"
echo "Wingman Startup Diagnostics"
echo "======================================================================"
echo ""

echo "1. Checking Python version..."
python --version

echo ""
echo "2. Checking required Python modules..."
python -c "import flask; print('✓ Flask installed')" || echo "✗ Flask missing"
python -c "import requests; print('✓ requests installed')" || echo "✗ requests missing"
python -c "import bcrypt; print('✓ bcrypt installed')" || echo "✗ bcrypt missing"
python -c "import cryptography; print('✓ cryptography installed')" || echo "✗ cryptography missing"

echo ""
echo "3. Checking application files..."
for file in app.py deployment_manager.py auth.py rbac.py errors.py; do
    if [ -f "/app/$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file MISSING"
    fi
done

echo ""
echo "4. Checking directories..."
for dir in /app/data /app/logs /app/templates/saved; do
    if [ -d "$dir" ]; then
        echo "✓ $dir exists"
        if [ -w "$dir" ]; then
            echo "  └─ writable"
        else
            echo "  └─ NOT WRITABLE"
        fi
    else
        echo "✗ $dir MISSING"
        echo "  └─ Creating..."
        mkdir -p "$dir"
    fi
done

echo ""
echo "5. Checking environment variables..."
echo "ENABLE_AUTH: ${ENABLE_AUTH:-not set}"
echo "FLASK_SECRET_KEY: ${FLASK_SECRET_KEY:0:20}... (${#FLASK_SECRET_KEY} chars)"
echo "ENABLE_SAML: ${ENABLE_SAML:-not set}"

echo ""
echo "6. Testing auth module import..."
python test_auth.py

echo ""
echo "7. Starting application..."
echo "======================================================================"
python app.py
