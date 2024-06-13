import asyncio
import os

from prometheus_fastapi_instrumentator import Instrumentator
import app.db.repository as repository
import app.db.db_init as db_init

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.chat.schemas import MessageSchema
from app.db.database import SessionLocal
from app.db.models import Message

KAFKA_INSTANCE = os.getenv("KAFKA_INSTANCE", "localhost:29092")


loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_INSTANCE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_init.init()
    loop.create_task(producer.start())
    yield
    await producer.stop()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/chat/static"), name="static")

Instrumentator().instrument(app).expose(app)

templates = Jinja2Templates(directory="app/chat/templates")


@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/send")
async def send_message(message_req: MessageSchema):
    message = Message(
        id=message_req.id,
        text=message_req.text,
        status=message_req.status,
        answer=message_req.answer
    )

    with SessionLocal() as db:
        repository.add_message(db, message)

    await producer.send("messages", message_req.model_dump_json().encode())
    return message


@app.get("/messages")
async def get_messages():
    with SessionLocal() as db:
        messages = {"messages": []}
        for message in repository.get_messages(db):
            msgSchema = MessageSchema(
                id=message.id,
                status=message.status,
                answer=message.answer,
                text=message.text
            )
            messages["messages"].append(msgSchema.model_dump())
        return messages


@app.get("/response/{message_id}")
async def get_response(message_id: str):
    with SessionLocal() as db:
        message = repository.get_message_by_id(db, message_id)
    if message.status == "success":
        return {"response": message.answer}
    return {"response": message.status}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
