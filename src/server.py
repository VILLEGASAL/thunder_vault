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
from routes.auth_route import Verify_Token
from database.db import Get_DB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone

from services.services import Insert_Into_Blacklist, Check_JTI_If_In_Blacklist, Delete_Refresh_Token_JTI_, Check_Token_If_Valid, Get_User_By_ID
import uuid
import time

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCES_TOKEN_EXPIRES_IN_SECONDS = os.getenv("ACCES_TOKEN_EXPIRES_IN_MINUTES")
REFRESH_TOKEN_EXPIRES_IN_SECONDS = os.getenv("REFRESH_TOKEN_EXPIRES_IN_MINUTES")

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

    if access_token:

        access_token_payload = jwt.decode(access_token, SECRET_KEY, algorithms=ALGORITHM, options={

            "verify_exp": False
        })
        
        access_token_jti = access_token_payload.get("jti", None)
        
        access_token_exp = access_token_payload.get("exp", None)
        
        convert = datetime.fromtimestamp(access_token_exp, tz=timezone.utc)
        
        try:
            if await Insert_Into_Blacklist(access_token_jti, convert, db):
                pass

        except Exception as e:
            pass
    
    if refresh_token:
        try:
            refresh_token_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM, options={

                "verify_exp": False
            })

            refresh_token_jti = refresh_token_payload.get("jti", None)

            if await Delete_Refresh_Token_JTI_(refresh_token_jti, db):
                pass

        except Exception as e:

            print(e)

            pass
            
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response

@app.get("/")
async def Home(request: Request, check_if_authorized=Depends(Check_Token_If_Valid), get_user_by_id = Depends(Get_User_By_ID), directory_exist: Optional[bool] = Query(default=False)):
    
    match check_if_authorized:
        case 0:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 1:
            main_folder: str = "file_server_directory"

            if not os.path.exists(main_folder):

                os.makedirs(main_folder)

                directories = os.listdir(path=main_folder)

                return template.TemplateResponse(request, "index.html", { 

                    "directories": directories,
                    "directory_exist": directory_exist,

                })
            
            else:

                match get_user_by_id:
                    case None:
                        return RedirectResponse(url="/auth/login", status_code=303)
                    case _:
                        user_directory_name = get_user_by_id[0].get("username", None)

                        directories = os.listdir(path=f"{main_folder}/{user_directory_name}")

                        directories.sort()

                        return template.TemplateResponse(request, "index.html", { 

                            "directories": directories,
                            "directory_exist": directory_exist,
                            "user": get_user_by_id[0].get("first_name", None)
                        })
        case 2:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 3:
            return RedirectResponse(url="/auth/refresh", status_code=303)


@app.get("/view_files")
def View_Files(request: Request, dir_name: Optional[str] = Query(default=None), get_user_by_id = Depends(Get_User_By_ID)):
    match get_user_by_id:
        case None:
            return RedirectResponse(url="/auth/login", status_code=303)
        case _:

            user_username = get_user_by_id[0].get("username", None)
            user_firstname = get_user_by_id[0].get("first_name", None)

            files: List[str] = os.listdir(f"file_server_directory/{user_username}/{dir_name}")

            return template.TemplateResponse(request, "view_files.html", {

                "directory_name" : dir_name,
                "files": files,
                "user": user_firstname
            })

@app.get("/download/{directory_name}/{file_name}")
def Download_File(directory_name: str, file_name: str, check_if_authorized = Depends(Check_Token_If_Valid), get_user_by_id = Depends(Get_User_By_ID)):

    match check_if_authorized:
        case 0:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 1:
            match get_user_by_id:
                case None:
                    return RedirectResponse(url="/auth/login", status_code=303)
                case _:
                    try:
                        user_username = get_user_by_id[0].get("username", None)

                        mime_type, _ = mimetypes.guess_type(f"file_server_directory/{user_username}/{directory_name}/{file_name}")

                        return FileResponse(

                            path=f"file_server_directory/{user_username}/{directory_name}/{file_name}",
                            filename=file_name,
                            media_type=mime_type or "application/octet-stream"
                        )
                    except Exception as e:
                        print("!!! ERROR IN DOWNLOADING !!!")

                        return RedirectResponse(url=f"/view_files/{directory_name}", status_code=303)
        case 2:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 3:
            return RedirectResponse(url="/auth/refresh", status_code=303)

@app.post("/mkdir")
def Mkdir(data: Annotated[Directory, Form()], get_user_by_id = Depends(Get_User_By_ID)):

    match get_user_by_id:
        case None:
            return RedirectResponse(url="/auth/login", status_code=303)
        case _:
            user_directory = get_user_by_id[0].get("username", None)

            new_directory = os.path.join("file_server_directory", user_directory, data.directory_name)

            if os.path.exists(new_directory):
                    print("!!! Existing !!!")

                    return RedirectResponse(url="/?directory_exist=True", status_code=303)

            new_directory = os.path.join(f"file_server_directory/{user_directory}", data.directory_name)

            try:
                os.mkdirs(new_directory)
            except Exception as e:
                print(e)
                return RedirectResponse(url="/", status_code=303)
            
            return RedirectResponse(url="/", status_code=303)

@app.post("/rmdir")
def Remove_Directory(dir_name: Optional[str] = Query(default=None), check_if_authorized = Depends(Check_Token_If_Valid), get_user_by_id = Depends(Get_User_By_ID)):

    match check_if_authorized:
        case 0:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 1:

            print("!! DELETING !!")

            match get_user_by_id:
                case None:
                    return RedirectResponse(url="/auth/login")
                case _:
                    if dir_name == None:
                        return RedirectResponse(url="/", status_code=303)
                    
                    else:
                        user_username = get_user_by_id[0].get("username", None)
                        
                        shutil.rmtree(f"file_server_directory/{user_username}/{dir_name}")

                        return RedirectResponse(url="/", status_code=303)
        case 2:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 3:
            return RedirectResponse(url="/auth/refresh", status_code=303)
        
     
@app.post("/rmfile")
def Remove_File(dir_name: str = Query(default=None), file_name: str = Query(default=None), check_if_authorized = Depends(Check_Token_If_Valid), get_user_by_id = Depends(Get_User_By_ID)):
    
    match check_if_authorized:
        case 0:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 1:

            match get_user_by_id:
                case None:
                    return RedirectResponse(url="/auth/login", status_code=303)
                case _:

                    try:

                        print("!!! DELETING A FILE !!!")

                        user_username = get_user_by_id[0].get("username", None)
                        print(user_username)
                        print(dir_name)
                        print(file_name)

                        file_path = os.path.join(f"file_server_directory/{user_username}/{dir_name}", file_name)

                        os.remove(file_path)

                        return RedirectResponse(url=f"/view_files?dir_name={dir_name}", status_code=303)
                        
                    except Exception as e:
                        print(f"!!! ERROR DELETING: {e} !!!")

                        return RedirectResponse(url="/", status_code=303)
        case 2:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 3:
            return RedirectResponse(url="/auth/refresh", status_code=303)

@app.post("/upload")
async def Upload_Files(dir_name: Optional[str] = Query(default=None), file_name: UploadFile = File(...), check_if_authorized = Depends(Check_Token_If_Valid), get_user_by_id = Depends(Get_User_By_ID)):

    match check_if_authorized:
        case 0:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 1:
            match get_user_by_id:
                case None:
                    return RedirectResponse(url="/auth/login", status_code=303)
                case _:

                    try:

                        user_username = get_user_by_id[0].get("username", None)

                        target_directory = os.path.join(f"file_server_directory/{user_username}/{dir_name}", file_name.filename)

                        with open(target_directory, "wb") as buffer:
                            shutil.copyfileobj(file_name.file, buffer)
                        
                        return RedirectResponse(url=f"/view_files?dir_name={dir_name}", status_code=303)

                    except Exception as e:
                        print("!!! ERROR UPLOADING!!!")
                        print(e)

                        return RedirectResponse(url=f"/", status_code=303)
        case 2:
            return RedirectResponse(url="/auth/login", status_code=303)
        case 3:
            return RedirectResponse(url="/auth/refresh", status_code=303)

            