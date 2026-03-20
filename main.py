import uvicorn


def main():
    uvicorn.run("src.server:app", host='127.0.0.1', port=5000, reload=True)

if __name__ == "__main__":
    main()
