import json
import asyncio
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

from app.db.database import SessionLocal
import app.db.repository as repository

KAFKA_INSTANCE = "localhost:29092"

loop = asyncio.get_event_loop()
consumer = AIOKafkaConsumer(
    "messages", bootstrap_servers=KAFKA_INSTANCE, loop=loop, request_timeout_ms=5000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    loop.create_task(consume())
    yield
    await consumer.stop()

app = FastAPI(lifespan=lifespan)


async def consume():
    await consumer.start()
    try:
        with SessionLocal() as db:
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
                message = repository.get_message_by_id(db, msg["id"])
                message.answer = "Good answer!"
                message.status = "success"
                db.commit()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
