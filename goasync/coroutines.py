import asyncio
import aiohttp
import time
import os

async def fetch_size(session, url, idx, url_info):
    async with session.get(url) as response:
        content_length = response.headers.get('Content-Length')

        if content_length is not None:
            size = int(content_length)
            url_info[idx] = [url.split("/")[-1], 0, int(size)]
            return size
        else:
            print(f"Could not determine the size of {url}")
            url_info[idx] = [url.split("/")[-1], 0, 0]
            return 0


async def cal_total_size(urls, url_info):
    async with aiohttp.ClientSession() as session:
        
        fetch_coroutines = []
        for idx, url in enumerate(urls):
            fetch_coroutines.append(fetch_size(session, url, idx, url_info))
        
        size_data = await asyncio.gather(*fetch_coroutines)
        
        return size_data
    
async def slogger(sema, session, idx, url, url_info, output_dir, Q):

    async with sema:
        async with session.get(url) as response:
            if response.status == 200:
                file_name = os.path.basename(url)
                with open(os.path.join(output_dir, url_info[idx][0]), 'wb') as file:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        file.write(chunk)
                        await Q["speed_queue"].put(len(chunk))

                await Q["done_queue"].put(('Download Complete', idx))
    

async def reciever(Q):

    ctr = 0
    last_time = time.time()
    while True:
        done, _ = await asyncio.wait(
            [Q[queue].get() for queue in Q],
            timeout=0.1  # Adjust the timeout as needed
        )
        
        for fut in done:
            message = fut.result()
            if message is None:
                # None is used as a sentinel to signal the end
                return
            print(f" {ctr}: {message}")

        if ctr == 100:
            return
        
        ctr+=1

        current_time = time.time()
        if current_time - last_time > 1:
            last_time = current_time
        print("=========== BAR")


async def get_urls(output_dir, urls, url_info):
    
    concurrency_limit = 5  # Set your desired concurrency limit
    sema = asyncio.Semaphore(concurrency_limit)

    Q = { "speed_queue" :asyncio.Queue(),
          "done_queue" : asyncio.Queue(),
          "error_queue" : asyncio.Queue(),
          "quit_queue" : asyncio.Queue()
    }


    async with aiohttp.ClientSession() as session:

        download_tasks = [slogger(sema, session, idx, url, url_info, output_dir, Q) for idx, url in enumerate(urls)]

        status_task = reciever(Q)
        await asyncio.gather(*download_tasks, status_task)


    print("DONE")
    print("EXITING")