# Functions required for Youtube authorization from googleapi

import os
import httpx
from urllib.parse import urlencode

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_oauth_url():
    '''
    Generates the Google authorization URL where the user is sent to log in and grant permission.
    '''
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str):
    '''
    Exchanges the authorization code for actual tokens.
    After the grant of permisson from google it would be redirected to REDIRECTED_URI
    which is auth/callback, which call the function oauth_callback, while redirecting
    google send a code (as a proof of permission) called authorisation code in the url
    (auth/callback) as params which is handled by fastAPI hence passed to the function
    as argument, so that code is passed to it.
    Now this function makes a post request on TOKEN_URL and get the access token from
    googleapi in exchange of the provided code.
    '''
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        return response.json()


async def refresh_access_token(refresh_token: str):
    '''
    Gets a new access token using a refresh token when the old one expires.
    '''
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
        return response.json()