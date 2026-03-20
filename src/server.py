from fastapi import FastAPI, Form, Query
from typing import Annotated, Optional
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os


class Directory(BaseModel):
    directory_name: str

class File(BaseModel):
    file_name: str

app = FastAPI()

template = Jinja2Templates(directory="templates")

static_file_directory = StaticFiles(directory="static")

app.mount("/static", static_file_directory, name="static")

@app.get("/")
def Home(request: Request, directory_exist: Optional[bool] = Query(default=False)):

    directories = os.listdir(path="file_server_directory")

    directories.sort()

    return template.TemplateResponse(request, "index.html", { 

        "directories": directories,
        "directory_exist": directory_exist
    })

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
        
        os.rmdir(f"file_server_directory/{dir_name}")

        return RedirectResponse(url="/", status_code=303)
     

@app.post("/upload")
def Upload_Files(file: Annotated[File, Form()]):
    
    print(file.file_name) 

    return {"Message": "Hello"}