import json
import logging
import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from uuid import uuid4

KAFKA_INSTANCE = "localhost:29092"


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('aiokafka')
logger.setLevel(logging.ERROR)


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = Field("processing")
    answer: str = Field(None)
    text: str


loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_INSTANCE)
consumer = AIOKafkaConsumer(
    "messages", bootstrap_servers=KAFKA_INSTANCE, loop=loop, request_timeout_ms=5000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await producer.start()
    loop.create_task(consume())
    yield
    await producer.stop()
    await consumer.stop()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="chat/static"), name="static")
templates = Jinja2Templates(directory="chat/templates")

messages: dict[str, Message] = {}

loop = asyncio.get_event_loop()


async def consume():
    await consumer.start()
    try:
        async for msg in consumer:
            await asyncio.sleep(5)
            print(
                "consumed: ",
                msg.topic,
                msg.partition,
                msg.offset,
                msg.key,
                msg.value,
                msg.timestamp,
            )
            msg = json.loads(msg.value)
            messages[msg["id"]].status = "success"
    finally:
        await consumer.stop()


@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/send")
async def send_message(message: Message):
    messages[message.id] = message
    print(message.model_dump_json())
    await producer.send("messages", message.model_dump_json().encode())
    return message


@app.get("/messages")
async def get_messages():
    return {"messages": list(messages.values())}


@app.get("/response/{message_id}")
async def get_response(message_id: int):
    message = messages[message_id]
    if message.status == "success":
        return {"response": message.answer}
    return {"response": message.status}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
