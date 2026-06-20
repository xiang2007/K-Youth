# def main():
#     print("Hello from week-3!")


# if __name__ == "__main__":
#     main()

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}