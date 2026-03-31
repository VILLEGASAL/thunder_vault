from fastapi import FastAPI, Form, Query, UploadFile, File, Path, HTTPException, Depends
from typing import Annotated, Optional, List, Dict
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import Response, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

#AUTHENTICATION & AUTHORIZATION LIBRARIES
from jose import JWTError, jwt, ExpiredSignatureError
#----------------------------------------------- 
from dotenv import load_dotenv, dotenv_values
import os
import shutil
import mimetypes

from routes import auth_route
from routes.auth_route import Verify_Token, Check_Token_In_DB, SESSIONS
from database.db import Get_DB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
import uuid
import time

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCES_TOKEN_EXPIRES_IN_SECONDS = os.getenv("ACCES_TOKEN_EXPIRES_IN_SECONDS")
REFRESH_TOKEN_EXPIRES_IN_SECONDS = os.getenv("REFRESH_TOKEN_EXPIRES_IN_SECONDS")

app = FastAPI()

template = Jinja2Templates(directory="templates")

static_file_directory = StaticFiles(directory="static")

app.mount("/static", static_file_directory, name="static")

app.include_router(

    auth_route.auth_route,
    prefix="/auth",
    tags=["auth_rooutes"]
)

class Directory(BaseModel):
    directory_name: str

@app.post("/logout")
async def Logout_User(request: Request, response: Response, db: AsyncSession = Depends(Get_DB)):
    
    response = RedirectResponse(url="/auth/login", status_code=303)

    access_token = request.cookies.get("access_token")
    
    refresh_token = request.cookies.get("refresh_token")
    try:
        if access_token:
            try:
            
                access_token_payload = jwt.decode(access_token, SECRET_KEY, algorithms=ALGORITHM, options={

                    "verify_exp": False
                })

                access_token_jti = access_token_payload.get("jti", None)

                access_token_exp = access_token_payload.get("exp", None)

                query = text("INSERT INTO blacklist_table (access_token_jti, expires_at) VALUES (:access_token_jti, :expires_at) ON CONFLICT DO NOTHING")

                values = {

                    "access_token_jti": access_token_jti,
                    "expires_at": datetime.fromtimestamp(access_token_exp, tz=timezone.utc)
                }

                await db.execute(query, values)
            
            except Exception as e:
                pass
        
        if refresh_token:
            try:
                refresh_token_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM, options={

                    "verify_exp": False
                })

                refresh_token_jti = refresh_token_payload.get("jti", None)

                query = text("DELETE FROM refresh_tokens WHERE jti = :jti")

                values = {

                    "jti": refresh_token_jti
                }        

                await db.execute(query, values)

            except Exception as e:

                print(e)

                pass
        
        await db.commit()
                
    finally:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response  
    


@app.get("/")
async def Home(request: Request, db: AsyncSession = Depends(Get_DB), directory_exist: Optional[bool] = Query(default=False)):

    access_token = request.cookies.get("access_token")

    main_folder: str = "file_server_directory"
    
    try:
        if access_token and Verify_Token(access_token):

            access_token_payload = jwt.decode(access_token, SECRET_KEY, algorithms=ALGORITHM)

            access_token_jti = access_token_payload.get("jti", None)
            
            query = text("SELECT * FROM blacklist_table WHERE access_token_jti = :access_token_jti")

            values = {

                "access_token_jti": access_token_jti
            }

            result = await db.execute(query, values)

            blacklist_jti = result.mappings().all()

            if not blacklist_jti:

                if not os.path.exists(main_folder):

                    os.makedirs(main_folder)

                    directories = os.listdir(path=main_folder)

                    return template.TemplateResponse(request, "index.html", { 

                        "directories": directories,
                        "directory_exist": directory_exist
                    })
                else:

                    directories = os.listdir(path=main_folder)

                    directories.sort()

                    return template.TemplateResponse(request, "index.html", { 

                        "directories": directories,
                        "directory_exist": directory_exist
                    })
            print("!!! BLACKLISTED !!!")
            return RedirectResponse("/auth/login", status_code=303)
        else:

            return RedirectResponse(url="/auth/login", status_code=303)       
    except ExpiredSignatureError:

        print("!!! EXPIRED ACCESS TOKEN !!!")
        # user = request.cookies.get("user")

        return RedirectResponse("/auth/refresh/")

    except JWTError:
        return HTTPException(status_code=403, detail="Access Token Expired")  

@app.get("/view_files/{dir_name}")
def View_Files(dir_name: str, request: Request):

    files: List[str] = os.listdir(f"file_server_directory/{dir_name}")

    return template.TemplateResponse(request, "view_files.html", {

        "directory_name" : dir_name,
        "files": files

    })

@app.get("/download/{directory_name}/{file_name}")
def Download_File(directory_name: str, file_name: str):

    mime_type, _ = mimetypes.guess_type("file_server_directory/{directory_name}/{file_name}")

    return FileResponse(

        path=f"file_server_directory/{directory_name}/{file_name}",
        filename=file_name,
        media_type=mime_type or "application/octet-stream"
    )


@app.post("/mkdir")
def Mkdir(data: Annotated[Directory, Form()]):

    if os.path.exists(f"file_server_directory/{data.directory_name}"):
            print("!!!Existing!!!")

            return RedirectResponse(url="/?directory_exist=True", status_code=303)

    new_directory = os.path.join("file_server_directory", data.directory_name)

    os.mkdir(new_directory) 
    
    return RedirectResponse(url="/", status_code=303)

@app.delete("/rmdir")
def Remove_Directory(dir_name: Optional[str] = Query(default=None)):

    print("!!DELETING!!")

    if dir_name == None:
        return RedirectResponse(url="/", status_code=303)
    
    else:
        
        shutil.rmtree(f"file_server_directory/{dir_name}")

        return RedirectResponse(url="/", status_code=303)
     

@app.post("/upload")
async def Upload_Files(dir_name: Annotated[str, Form()], file_name: UploadFile = File(...)):

    target_directory = os.path.join("file_server_directory", dir_name, file_name.filename)

    with open(target_directory, "wb") as buffer:
        shutil.copyfileobj(file_name.file, buffer)
    
    return RedirectResponse(url="/", status_code=303)