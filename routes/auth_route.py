from fastapi import APIRouter, Form, HTTPException, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Annotated, List, Dict, Optional
from fastapi.responses import RedirectResponse, Response
from passlib.context import CryptContext
from dotenv import load_dotenv

from jose import jwt, JWTError, ExpiredSignatureError
from datetime import timedelta, datetime, timezone
import time
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
from database.db import Get_DB

import uuid

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCES_TOKEN_EXPIRES_IN_SECONDS = os.getenv("ACCES_TOKEN_EXPIRES_IN_SECONDS")
REFRESH_TOKEN_EXPIRES_IN_SECONDS = os.getenv("REFRESH_TOKEN_EXPIRES_IN_SECONDS")


SESSIONS: Dict = {} 

auth_route = APIRouter()

template = Jinja2Templates(directory="templates")

static_file_directory = StaticFiles(directory="static")

auth_route.mount("/static", static_file_directory, name="static")


class User(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    username: str
    password: str


password_context = CryptContext(schemes=["argon2"], deprecated="auto")

async def Check_Token_In_DB(access_token: str, db: AsyncSession):

    try:
        query = text("SELECT access_token FROM tokens_table WHERE access_token = :access_token")
        values = {

            "access_token": access_token
        }

        result = await db.execute(query, values)

        token = result.fetchone()

        if token:
            return True
        
        return False
    
    except SQLAlchemyError:

        print("ERRRR")
        return False

def Generate_Token(data: Dict, expire_time: timedelta):

    data["exp"] = int((datetime.now(timezone.utc) + expire_time).timestamp())
    
    data["jti"] = str(uuid.uuid4())

    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def Create_Tokens(user: str):
    
    access_token = Generate_Token({"user":user}, timedelta(minutes=int(ACCES_TOKEN_EXPIRES_IN_SECONDS)))
    refresh_token = Generate_Token({"user":user}, timedelta(minutes=int(REFRESH_TOKEN_EXPIRES_IN_SECONDS)))

    return {

        "access_token": access_token,
        "refresh_token": refresh_token
    }


def Refresh_Token(ref_token: str, user: str):

    try:

        if jwt.decode(ref_token, SECRET_KEY, algorithms=ALGORITHM):
            
            return Create_Tokens(user)
    
    except ExpiredSignatureError:

        return False
    
    except JWTError:

        return False

def Verify_Token(token: str):
    
    if jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM):
        return True
    
    return False

@auth_route.get("/refresh")
async def Get_New_Access_Token(request: Request, response: Response, db: AsyncSession = Depends(Get_DB)):

    refresh_token = request.cookies.get("refresh_token")

    success_redirect = RedirectResponse("/", status_code=303)

    failed_redirect = RedirectResponse("/auth/login", status_code=303)

    try:

        if refresh_token and Verify_Token(refresh_token):

            refresh_token_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM)

            user = refresh_token_payload.get("user", None)

            refresh_token_jti = refresh_token_payload.get("jti", None)
        
            query = text("SELECT * FROM refresh_tokens WHERE jti = :jti")

            values = {

                "jti": refresh_token_jti
            }

            result = await db.execute(query, values)

            refresh_tokens_jti = result.mappings().all()

            #Check if refresh token is in the database. If not, it has been revoked or deleted
            if refresh_tokens_jti:
                
                print("!!! GENERATING NEW ACCESS TOKEN !!!")
                new_access_token = Generate_Token({"user": user}, timedelta(minutes=int(ACCES_TOKEN_EXPIRES_IN_SECONDS)))

                success_redirect.set_cookie(

                    key="access_token",
                    value=new_access_token,
                    httponly=True,
                    secure=True,
                    samesite="lax"
                )

                return success_redirect

    except ExpiredSignatureError:

        return failed_redirect

@auth_route.get("/signup")
def Signup_Page(request: Request, error: Optional[bool] = Query(default=False)):

    return template.TemplateResponse(request, "signup.html", {

        "route": "/auth/signup",
        "error": error
    })

@auth_route.post("/signup")
async def Signup(user_credentials: Annotated[User, Form()], db: AsyncSession = Depends(Get_DB)):

    user_credentials.password = password_context.hash(user_credentials.password)

    firstname = user_credentials.firstname
    lastname = user_credentials.lastname
    username = user_credentials.username
    password = user_credentials.password

    query = text("INSERT INTO users_table (first_name, last_name, username, password) VALUES (:firstname, :lastname, :username, :password)")

    try:
        await db.execute(query, 
            {
                "firstname": firstname,
                "lastname": lastname,
                "username": username, 
                "password": password
            })

        await db.commit()

        return RedirectResponse("/auth/login", status_code=303)
    
    except IntegrityError as e:

        return RedirectResponse(url="/auth/signup?error=True", status_code=303)

    except SQLAlchemyError:

        await db.rollback()

        return HTTPException(status_code=500, detail="Database Error Occured")

@auth_route.get("/login")
def Login_Page(request: Request, error: Optional[bool] = Query(default=None)):

    return template.TemplateResponse(request, "login.html", {

        "error": error
    })

@auth_route.post("/login")
async def Login(user_credentials: Annotated[User, Form()], db: AsyncSession = Depends(Get_DB)):
    
    from services.services import Get_User_By_Username, Insert_Refresh_Token

    username_input = user_credentials.username
    password_input = user_credentials.password

    try:

        user = await Get_User_By_Username(username_input, db)

        if user:
            
            user_password = user[0].get("password", None)
            user_id = user[0].get("user_id", None)

            success_redirect = RedirectResponse(url="/", status_code=303)
            
            if password_context.verify(password_input, user_password):
                
                access_token = Generate_Token({"user": user_id}, timedelta(minutes=int(ACCES_TOKEN_EXPIRES_IN_SECONDS)))
                refresh_token = Generate_Token({"user": user_id}, timedelta(minutes=int(REFRESH_TOKEN_EXPIRES_IN_SECONDS)))

                refresh_token_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM)

                refresh_token_exp = refresh_token_payload.get("exp", None)

                #COnvert the exp to timestamp

                expires_at = datetime.fromtimestamp(refresh_token_exp, tz=timezone.utc)

                if await Insert_Refresh_Token(refresh_token_payload.get("jti", None), refresh_token_payload.get("user", None), expires_at, db):

                    success_redirect.set_cookie(

                        key="access_token",
                        value=access_token,
                        httponly=True,
                        secure=True,
                        samesite="lax"
                    )

                    success_redirect.set_cookie(

                        key="refresh_token",
                        value=refresh_token,
                        httponly=True,
                        secure=True,
                        samesite="lax"
                    )

                    return success_redirect
                else:
                    print("ERROR INSERTING>>>>>")

                    return RedirectResponse("/auth/login")
        return RedirectResponse(url="/auth/login?error=True", status_code=303)
    
    except SQLAlchemyError as e:

        return HTTPException(status_code=500, detail="Database Error!")

