import uvicorn

from config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("api.server:app", host=API_HOST, port=API_PORT)
