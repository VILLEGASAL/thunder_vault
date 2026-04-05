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


from services.services import Signup_User, Check_Token_If_Valid, Verify_Token, Generate_Token, Check_If_Refresh_Token_Is_Valid
import uuid

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCES_TOKEN_EXPIRES_IN_SECONDS = os.getenv("ACCES_TOKEN_EXPIRES_IN_MINUTES")
REFRESH_TOKEN_EXPIRES_IN_SECONDS = os.getenv("REFRESH_TOKEN_EXPIRES_IN_MINUTES")


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



@auth_route.get("/refresh")
async def Get_New_Access_Token(request: Request, dependency = Depends(Check_If_Refresh_Token_Is_Valid), db: AsyncSession = Depends(Get_DB)):

    success_redirect = RedirectResponse(url="/", status_code=303)
    
    failed_redirect = RedirectResponse(url="/auth/login", status_code=303)

    refresh_token = request.cookies.get("refresh_token", None)

    refresh_token_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM, options = {
        "verify_exp": False
    })

    user = refresh_token_payload.get("user", None)

    match dependency:
        case 0:
            return failed_redirect
        case 1:
            new_access_token = Generate_Token({"user": user}, timedelta(minutes=int(ACCES_TOKEN_EXPIRES_IN_SECONDS)))

            success_redirect.set_cookie(

                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=True,
                samesite="lax"
            )

            return success_redirect
        case 2:
            return failed_redirect
        case 3:
            return failed_redirect
        case 4:
            return failed_redirect
        case 5:
            return failed_redirect

@auth_route.get("/signup")
def Signup_Page(request: Request, dependency = Depends(Check_Token_If_Valid), error: Optional[bool] = Query(default=False)):

    return_template = template.TemplateResponse(request, "signup.html", {

        "error": error
    })

    match dependency:
        case 0:
            print("!!!NO TOKENS FOUND!!!")
            return return_template
        case 1:
            return RedirectResponse(url="/", status_code=303)
        case 2:
            return return_template
        case 3:
            return return_template

    if not dependency:
        return RedirectResponse(url="/", status_code=303)

    return template.TemplateResponse(request, "signup.html", {

        "route": "/auth/signup",
        "error": error
    })

@auth_route.post("/signup")
async def Signup(user_credentials: Annotated[User, Form()], db: AsyncSession = Depends(Get_DB)):

    user_credentials.password = password_context.hash(user_credentials.password)
    
    response = await Signup_User(user_credentials, db)

    match response:
        case 0:
            return RedirectResponse("/auth/signup?error=True", status_code=303)
        case 1:
            return RedirectResponse("/auth/signup", status_code=303)
        case _:
            new_directory = os.path.join("file_server_directory", response)

            os.mkdir(new_directory) 
            print(f"!!! FROM SIGNUP ROUTE : {response}")
            return RedirectResponse("/auth/login", status_code=303)

@auth_route.get("/login")
def Login_Page(request: Request, dependency = Depends(Check_Token_If_Valid), error: Optional[bool] = Query(default=None)):

    match dependency:
        case 0:
            print("!!!NO TOKENS FOUND!!!")
            return template.TemplateResponse(request, "login.html", {

                "error": error
            })
        case 1:
            return RedirectResponse(url="/", status_code=303)
        case 2:
            return template.TemplateResponse(request, "login.html", {

                "error": error
            })
        case 3:
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

                #Convert the exp to timestamp
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
                    print("!!! ERROR INSERTING !!!")

                    return RedirectResponse("/auth/login")
        return RedirectResponse(url="/auth/login?error=True", status_code=303)
    
    except SQLAlchemyError as e:

        return HTTPException(status_code=500, detail="Database Error!")

