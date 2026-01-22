from supabase import create_client, Client
from django.conf import settings
# from gotrue.errors import AuthApiError
from django.contrib.auth.models import User

from .models import Profile

# Initialize Supabase client globally
try:
    SUPABASE_URL = settings.SUPABASE_URL
    SUPABASE_KEY = settings.SUPABASE_KEY
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client initialized successfully.")
    else:
        supabase = None
        print("WARNING: Supabase URL or Key not found in settings. Supabase functions will not work.")
except Exception as e:
    supabase = None
    print(f"ERROR: Failed to initialize Supabase client: {e}")
    import traceback
    traceback.print_exc()


def send_password_reset_otp_email(email: str) -> dict:
    """
    Sends a One-Time Password (OTP) to the user's email for password reset.
    This uses Supabase's passwordless sign-in OTP mechanism, which can then be
    leveraged for password reset after verification.

    Args:
        email (str): The email address of the user.

    Returns:
        dict: A dictionary indicating success or failure.
              {'success': True, 'message': 'OTP sent.'}
              {'success': False, 'error': 'Error message'}
    """
    if not supabase:
        return {'success': False, 'error': 'Supabase client not initialized.'}

    try:
        # Call sign_in_with_otp.
        # In newer versions of supabase-py, if an error occurs, it typically raises an AuthApiError.
        # If no error is raised, it means the request to send the OTP was successful.
        response = supabase.auth.sign_in_with_otp({"email": email}) # This call itself will raise an error on failure

        # If we reach here, it means no AuthApiError was raised.
        # The response object for sign_in_with_otp might contain user/session if already signed in,
        # or it might just indicate that the OTP was sent for an existing user (user/session might be None).
        # For password reset, the primary goal is that the OTP email was sent.
        print(f"OTP initiated for: {email}")
        return {'success': True, 'message': 'If an account with that email exists, an OTP has been sent.'}

    except Exception as e:
        print(f"Supabase Auth API Error sending OTP for {email}: {e.message}")
        import traceback
        traceback.print_exc()
        # For security, we still return a generic message to the frontend
        # to avoid exposing whether an email exists in the system.
        return {'success': False, 'error': e.message}
    except Exception as e:
        print(f"Unexpected error sending OTP for {email}: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': f'An unexpected error occurred: {e}'}


def verify_otp_and_update_email_verified(email: str, otp_code: str) -> dict:
    """
    Verifies the OTP and updates the user's password using Supabase.

    Args:
        email (str): The user's email.
        otp_code (str): The OTP received by the user.
        new_password (str): The new password to set.

    Returns:
        dict: A dictionary indicating success or failure.
              {'success': True, 'message': 'Password updated.'}
              {'success': False, 'error': 'Error message'}
    """
    if not supabase:
        return {'success': False, 'error': 'Supabase client not initialized.'}

    try:
        # ✅ FIX: Pass a single dictionary as required by supabase-py
        verify_response = supabase.auth.verify_otp({
            "email": email,
            "token": otp_code,
            "type": "email"  # or "recovery" depending on your flow
        })

        if getattr(verify_response, "error", None):
            print(f"Supabase error verifying OTP for {email}: {verify_response.error.message}")
            return {'success': False, 'error': verify_response.error.message}

        session = getattr(verify_response, "session", None)
        if not session:
            return {'success': False, 'error': 'OTP verified but no active session returned.'}

        # 2. Update the user's password
        # update_response = supabase.auth.update_user({"password": new_password})
        # User = get_user_model()
        try:
            user = User.objects.get(email=email)
            profile = Profile.objects.get(user=user)
            profile.email_verified = True
            profile.save()
            print(f"Email Verified for email: {email}")
        except User.DoesNotExist:
            return {'success': False, 'error': 'User does not exist here.'}

        print(f"Email Verfied successfully for: {email}")
        return {'success': True, 'message': 'Email Verified successfully.'}

    except Exception as e:
        print(f"Supabase Auth API Error during OTP verification or password update for {email}: {e.message}")
        return {'success': False, 'error': e.message}
    except Exception as e:
        print(f"Unexpected error during OTP verification or password update for {email}: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': f'An unexpected error occurred: {e}'}
    

def verify_otp_and_update_password(email: str, otp_code: str, new_password: str) -> dict:
    """
    Verifies the OTP and updates the user's password using Supabase.

    Args:
        email (str): The user's email.
        otp_code (str): The OTP received by the user.
        new_password (str): The new password to set.

    Returns:
        dict: A dictionary indicating success or failure.
              {'success': True, 'message': 'Password updated.'}
              {'success': False, 'error': 'Error message'}
    """
    if not supabase:
        return {'success': False, 'error': 'Supabase client not initialized.'}

    try:
        # ✅ FIX: Pass a single dictionary as required by supabase-py
        verify_response = supabase.auth.verify_otp({
            "email": email,
            "token": otp_code,
            "type": "email"  # or "recovery" depending on your flow
        })

        if getattr(verify_response, "error", None):
            print(f"Supabase error verifying OTP for {email}: {verify_response.error.message}")
            return {'success': False, 'error': verify_response.error.message}

        session = getattr(verify_response, "session", None)
        if not session:
            return {'success': False, 'error': 'OTP verified but no active session returned.'}

        # 2. Update the user's password
        # update_response = supabase.auth.update_user({"password": new_password})
        # User = get_user_model()
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            print(f"Password updated via Django for: {email}")
        except User.DoesNotExist:
            return {'success': False, 'error': 'User does not exist here.'}

        print(f"Password successfully updated for: {email}")
        return {'success': True, 'message': 'Password updated successfully.'}

    except Exception as e:
        print(f"Supabase Auth API Error during OTP verification or password update for {email}: {e.message}")
        return {'success': False, 'error': e.message}
    except Exception as e:
        print(f"Unexpected error during OTP verification or password update for {email}: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': f'An unexpected error occurred: {e}'}