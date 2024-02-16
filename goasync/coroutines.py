import asyncio
import aiohttp
import time
import sys
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
                        await Q["speed_queue"].put(sys.getsizeof(chunk))

                await Q["done_queue"].put(('DONE', idx))
    

async def reciever(Q, url_info):

    ctr = 0
    total_bytes = 0
    current_bytes =0
    last_time = time.time()
    to_fetch = len(url_info)
    fetched =0

    while True:

        #Get speed queue
        last_checkpoint_time =  time.time()
        while True:
            try:
                bytes = await asyncio.wait_for(Q["speed_queue"].get(), timeout=0.1)
                if bytes is not None:
                    total_bytes +=bytes
                    current_bytes += bytes
                else:
                    break
                current_checkpoint_time = time.time()
                if current_checkpoint_time-last_time >= 0.5:
                    break

            except asyncio.TimeoutError:
                #Exception while reading Speed QUeue
                #print("Timeout Error !")
                break


        #Get Done Queue
        try:
            msg = await asyncio.wait_for(Q["done_queue"].get(), timeout=0.1)
            if msg is not None:
                sys.stdout.write(f"\r\033[K[DONE] {url_info[msg[1]][0]}\n")
                sys.stdout.flush()
                fetched+=1
        except asyncio.TimeoutError:
            #print("timeout error on Error Queue")
            pass

        
        #Get Error Queue
        try:
            msg = await asyncio.wait_for(Q["error_queue"].get(), timeout=0.1)
            if msg is not None:
                sys.stdout.write(f"\r\033[K[ERROR] {url_info[msg[1]][0]}\n")
                sys.stdout.flush()
        except asyncio.TimeoutError:
            #print("timeout error on Error Queue")
            pass

        current_time = time.time()
        if current_time - last_time > 1:
            last_time = current_time


            bar_length = 50
            filled_len = int((bar_length/to_fetch)*fetched)
            bar = '█'*filled_len + '-'*(bar_length-filled_len)
            percent = (fetched/to_fetch)*100
            speed = (2*current_bytes)/(1024*1024)
            sys.stdout.write(f"\r\033[KProgress |{bar}| {fetched}/{to_fetch} {percent:.2f}% @{speed:.2f} MB/s")
            sys.stdout.flush()



            #print(f"=========== BAR {ctr} {fetched}/{to_fetch} @{(2*current_bytes)/(1024*1024)}")
            current_bytes = 0

        if fetched == to_fetch:
            print(f"Fetched {total_bytes/(1024*1024)}")
            return True

        if ctr == 500:
            return
        
        ctr+=1


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

        status_task = reciever(Q, url_info)
        await asyncio.gather(*download_tasks, status_task)


    print("DONE")
    print("EXITING")