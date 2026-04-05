from fastapi import Request, Depends
from fastapi.responses import RedirectResponse, Response
from typing import Dict
from database.db import Get_DB
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import BaseModel
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCES_TOKEN_EXPIRES_IN_SECONDS = os.getenv("ACCES_TOKEN_EXPIRES_IN_MINUTES")
REFRESH_TOKEN_EXPIRES_IN_SECONDS = os.getenv("REFRESH_TOKEN_EXPIRES_IN_MINUTES")

class User(BaseModel):
    firstname: str
    lastname: str
    username: str
    password: str


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

async def Get_User_By_Username(username: str, db: AsyncSession):
    
    try:
        query = text("SELECT * FROM users_table WHERE username = :username")

        values = {

            "username": username
        }

        result = await db.execute(query, values)

        user = result.mappings().all()

        return user
    
    except SQLAlchemyError as e:

        print(e)

        return False
    
async def Insert_Refresh_Token(jti: str, user_id: str, expires_at:str, db: AsyncSession) -> bool:
    
    try:
        query = text("INSERT INTO refresh_tokens (jti, user_id, expires_at) VALUES (:jti, :user_id, :expires_at)")

        values = {

            "jti": jti,
            "user_id": user_id,
            "expires_at": expires_at
        }

        await db.execute(query, values)

        await db.commit()

        return True

    except SQLAlchemyError as e:
        
        print(e)

        return False

async def Insert_Into_Blacklist(uuid: str, exp: str, db: AsyncSession):

    try:

        query = text("INSERT INTO blacklist_table (access_token_jti, expires_at) VALUES (:jti, :expires_at) ON CONFLICT DO NOTHING")

        values = {

            "jti": uuid,
            "expires_at": exp
        }

        await db.execute(query, values)
        
        await db.commit()

        return True

    except Exception as e:
        await db.rollback()
        print("!!! ERROR IN INSERTING TO BLACK LIST !!!")
        print(e)
        return False
    
async def Check_JTI_If_In_Blacklist(jti: str, db: AsyncSession) -> bool:
    
    try:
        query = text("SELECT * FROM blacklist_table WHERE access_token_jti = :jti")

        values = {

            "jti": jti
        }

        result = await db.execute(query, values)

        access_token_jti = result.mappings().all()

        # Check if the jti is in the blacklist 
        if access_token_jti:
            print("!!! ACCESS TOKEN IS BLACKLISTED !!!")
            return True
        
        print("!!! GRANTED !!!")

        return False

    except Exception as e:
        await db.rollback()

        print(e)

        return False
    
async def Delete_Refresh_Token_JTI_(jti: str, db: AsyncSession) -> bool:
    
    try:
        query = text("DELETE FROM refresh_tokens WHERE jti = :jti")

        values = {

            "jti":jti
        }
        
        await db.execute(query, values)

        await db.commit()

        return True
        
    except Exception as e:
        await db.rollback()
        print(e)
        return False
    
async def Signup_User(user: User, db: AsyncSession):

    try:
        query = text("INSERT INTO users_table (first_name, last_name, username, password) VALUES (:fname, :lname, :username, :password)")

        values = {

            "fname": user.firstname,
            "lname": user.lastname,
            "username": user.username,
            "password": user.password
        }
        
        await db.execute(query, values)

        await db.commit()

        return user.username
    
    except IntegrityError as e:
        print("!!! DUPLICATION !!! ")

        print(e)

        return 0
    
    except Exception as e:
        print(e)

        return 1
    
async def Get_User_By_ID(request: Request, db: AsyncSession = Depends(Get_DB)):
    
    access_token = request.cookies.get("access_token")

    if not access_token:
        return None
    
    acces_token_payload = jwt.decode(token=access_token, key=SECRET_KEY, algorithms=ALGORITHM, options={

        "verify_exp": False
    })

    user_id = acces_token_payload.get("user", None)
    
    query = text("SELECT * FROM users_table WHERE user_id = :id")
    
    values = {

        "id": user_id
    }

    try:
        result = await db.execute(query, values)

        user = result.mappings().all()

        if user:
            return user
        
        return None

    except SQLAlchemyError as e:

        print(e)
        return None

async def Check_Token_If_Valid(request: Request, db: AsyncSession = Depends(Get_DB)):

    access_token = request.cookies.get("access_token", None)
    
    if not access_token:
        #Return 0 if there is no access token in the cookie.
        return 0
    
    try:
        if Verify_Token(access_token):
            
            access_token_payload = jwt.decode(access_token, SECRET_KEY, algorithms=ALGORITHM, options={

                "verify_exp": False
            })

            access_token_jti = access_token_payload.get("jti", None)

            # If it returns True, then that means the JWT is in blacklist and it is invalid.
            if not await Check_JTI_If_In_Blacklist(jti=access_token_jti, db=db):
                
                # Return 1 if the access token is not expired and not in the blacklist
                return 1

            #Return 2 if the access token is in the blacklist
            print("!!! ACCESS TOKEN IS IN BLACKLIST !!!")
            return 2

    except ExpiredSignatureError as e:
        
        print("!!! TOKEN EXPIRED !!!")
        
        #Return 3 if the access token has expired
        return 3

async def Check_If_Refresh_Token_Is_Valid(request: Request, response: Response, db: AsyncSession = Depends(Get_DB)):
    
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        return 0
    
    try:
        if Verify_Token(refresh_token):
            
            refresh_token_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM, options={

                "verify_exp": False
            })

            refresh_token_jti = refresh_token_payload.get("jti", None)

            query = text("SELECT * FROM refresh_tokens WHERE jti = :jti")

            values = {

                "jti": refresh_token_jti
            }

            try:
                response = await db.execute(query, values)

                jtis = response.mappings().all()

                if jtis:
                    return 1
                
                return 2

            except SQLAlchemyError as e:
                print("!!! SQL ALCHEMY ERROR !!!")
                print(e)

                return 3
        return 4
    except ExpiredSignatureError as e:
        print("!!! REFRESH TOKEN EXPIRED !!!")
        return 5