from fastapi import FastAPI, Form, Query, UploadFile, File, Path
from typing import Annotated, Optional, List
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import shutil
import mimetypes


class Directory(BaseModel):
    directory_name: str

app = FastAPI()

template = Jinja2Templates(directory="templates")

static_file_directory = StaticFiles(directory="static")

app.mount("/static", static_file_directory, name="static")

@app.get("/")
def Home(request: Request, directory_exist: Optional[bool] = Query(default=False)):

    main_folder: str = "file_server_directory"

    if not os.path.exists(main_folder):
        os.makedirs(main_folder)

    directories = os.listdir(path=main_folder)

    directories.sort()

    return template.TemplateResponse(request, "index.html", { 

        "directories": directories,
        "directory_exist": directory_exist
    })

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