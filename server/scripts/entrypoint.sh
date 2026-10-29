#!/bin/bash
set -e

SSM_BASE_PATH="/bullbear/production"
AWS_REGION="eu-north-1"
export AWS_REGION

# ---------------------------
# Helper Function
# ---------------------------
get_ssm_parameter() {
    local param_name=$1
    >&2 echo "Attempting to fetch SSM parameter: $param_name"
    aws ssm get-parameter \
        --name "$param_name" \
        --query 'Parameter.Value' \
        --output text \
        --with-decryption 2>/dev/null || echo ""
}

# ---------------------------
# Fetch Parameters from SSM
# ---------------------------
echo "Fetching and setting environment variables from Parameter Store..."

export SECRET_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/django_secret_key")
export ALLOWED_HOSTS_STRING=$(get_ssm_parameter "${SSM_BASE_PATH}/app/allowed_hosts")
export CSRF_TRUSTED_ORIGINS_STRING=$(get_ssm_parameter "${SSM_BASE_PATH}/app/csrf_trusted_origins")
export CORS_ALLOWED_ORIGINS_STRING=$(get_ssm_parameter "${SSM_BASE_PATH}/app/cors_allowed_origins")

export DJANGO_ENV="production"
export DEBUG="False"

export DB_NAME=$(get_ssm_parameter "${SSM_BASE_PATH}/db_name")
export DB_USER=$(get_ssm_parameter "${SSM_BASE_PATH}/db_user")
export DB_PASSWORD=$(get_ssm_parameter "${SSM_BASE_PATH}/password")
export DB_HOST=$(get_ssm_parameter "${SSM_BASE_PATH}/db_host")
export DB_PORT=5432

export POLYGON_MOCK_MODE=$(get_ssm_parameter "${SSM_BASE_PATH}/polygon/mock_mode")
export ALPHA_VANTAGE_API_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/alpha_vantage/api_key")
export BB_STEADY_APIKEY=$(get_ssm_parameter "${SSM_BASE_PATH}/steadyapi/api_key")
export SUPABASE_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/supabase/key")
export SUPABASE_URL=$(get_ssm_parameter "${SSM_BASE_PATH}/supabase/url")

export LOGO_DEV_PUBLISHABLE_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/logodev/token")

export USE_S3=$(get_ssm_parameter "${SSM_BASE_PATH}/s3/use_s3")
export AWS_STORAGE_BUCKET_NAME=$(get_ssm_parameter "${SSM_BASE_PATH}/s3/bucket_name")

export TWILIO_ACCOUNT_ID=$(get_ssm_parameter "${SSM_BASE_PATH}/twilio/account_id")
export TWILIO_AUTH_TOKEN=$(get_ssm_parameter "${SSM_BASE_PATH}/twilio/auth_token")
export POLYGON_API_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/polygon/api_key")

# OpticOdds sportsbook feed used by the admin sportsbook POC.
export OPTIC_ODDS_API_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/optic_odds/api_key")
export ADMIN_SERVER_API_KEY=$(get_ssm_parameter "${SSM_BASE_PATH}/admin_server/api_key")
OPTIC_ODDS_SSM_BASE_URL=$(get_ssm_parameter "${SSM_BASE_PATH}/optic_odds/base_url")
export OPTIC_ODDS_BASE_URL="${OPTIC_ODDS_SSM_BASE_URL:-${OPTIC_ODDS_BASE_URL:-https://api.opticodds.com/api/v3}}"
SPORTSBOOK_MODE_SSM=$(get_ssm_parameter "${SSM_BASE_PATH}/sportsbook/mode")
export SPORTSBOOK_MODE="${SPORTSBOOK_MODE_SSM:-${SPORTSBOOK_MODE:-auto}}"

echo "✅ All environment variables fetched and set."

# ---------------------------
# Wait for Database
# ---------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Waiting for database at $DB_HOST:$DB_PORT..."
"$SCRIPT_DIR/wait-for-it.sh" "$DB_HOST:$DB_PORT" -t 100 -- echo "✅ Database is up!"

# ---------------------------
# Migrations & Static Files
# ---------------------------
echo "Running migrations..."
env PYTHONPATH=src python src/manage.py migrate --noinput

echo "Collecting static files to S3..."
env PYTHONPATH=src python src/manage.py collectstatic --noinput

# ---------------------------
# Superuser Creation
# ---------------------------
DJANGO_SUPERUSER_USERNAME="admin"
DJANGO_SUPERUSER_EMAIL="admin@bullbear.com"
DJANGO_SUPERUSER_PASSWORD="admin101"

echo "Ensuring superuser exists..."
env PYTHONPATH=src python src/manage.py shell <<EOF
from django.contrib.auth import get_user_model
from user.models import Profile, KYCProfile
User = get_user_model()
user, created = User.objects.get_or_create(username="${DJANGO_SUPERUSER_USERNAME}", defaults={
    "email": "${DJANGO_SUPERUSER_EMAIL}"
})
if created:
    user.set_password("${DJANGO_SUPERUSER_PASSWORD}")
    user.is_staff = True
    user.is_superuser = True
    user.save()
profile, _ = Profile.objects.get_or_create(user=user)
profile.is_admin=True
profile.save()
KYCProfile.objects.get_or_create(user=user)
print("✅ Superuser verified or created.")
EOF

# ---------------------------
# Start Services
# ---------------------------
if [ -n "$RUN_TASK" ] && [ "$RUN_TASK" != "" ]; then
    echo "Running specified task: $RUN_TASK"
    exec env PYTHONPATH=src python src/manage.py "$RUN_TASK"
else
    echo "Starting Django Q cluster in background..."
    env PYTHONPATH=src python src/manage.py qcluster &

    echo "Starting Gunicorn server..."
    exec env PYTHONPATH=src gunicorn \
        --timeout 300 \
        --bind 0.0.0.0:8000 \
        core.wsgi:application
fi
