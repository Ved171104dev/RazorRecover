import os
from redis import Redis
from rq import Queue,Worker
if __name__=="__main__":
    connection=Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"))
    Worker([Queue("razorrecover",connection=connection)],connection=connection).work(with_scheduler=True)
