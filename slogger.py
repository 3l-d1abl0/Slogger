#!/usr/bin/python3
import os
import sys
import time
import argparse
import threading
import urllib.request
from colorama import Fore, Back, Style
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

lock = threading.Lock()

class Slogger:

    @staticmethod
    def url_encode(urls):
        new_urls = []
        for url in urls:
            url_split = url.split("/")
            new_urls.append(url_split[0]+"//"+url_split[2]+"/"+urllib.parse.quote("/".join(url_split[3:])))

        return new_urls

    def __init__(self, url_file):

        #read the file and setup the urls
        self.urls = [url.strip().replace(" ","%20") for url in open(url_file).readlines()]
        self.new_urls = self.urls #self.url_encode(self.urls)
        self.url_size = {}
        '''
        for url in self.new_urls:
            print (url)
        #print(self.new_urls)
        '''

    def fetch_size(self, idx, url):

        '''
        headers={ "Accept-Language": "en_US", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"}
        '''
        try:
            req = urllib.request.Request(url)
            req.add_header("Accept-Language", "en-US,en;q=0.9,hi;q=0.8")
            req.add_header("Connection","keep-alive")
            #req.add_header("Host","cdn9.git.ir")
            req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36")
            site = urllib.request.urlopen(req)
            print(site)
        except Exception as e:
            print(e)
            '''
            print("Oops!", dir(e), "occurred.")
            print(e.reason)
            print(e.info)
            print(e.msg)
            print(e.name)
            print(e.strerror)
            print(e.status)'''
            return 0

        meta = site.info()

        self.url_size[idx] = [url.split("/")[-1], 0, int(meta['Content-Length'])]

        #print("Thread : {}".format(threading.current_thread().name))
        print("{} {} {}: {} --> {}{}{:.2f}MB ({} bytes){} \n".format(Fore.RED, threading.current_thread().name, Style.RESET_ALL, url.split("/")[-1], Fore.GREEN, Back.BLACK, int(meta['Content-Length'])/(1024*1024), int(meta['Content-Length']), Style.RESET_ALL))
        return int(meta['Content-Length'])

    @staticmethod
    def print_relative_size(size_bytes):

        if int(size_bytes/(1024*1024*1024)) >0:
            print("Total Size : {:.2f} GB ({} bytes)".format(size_bytes/(1024*1024*1024), size_bytes))
            return "{:.2f} GB".format(size_bytes/(1024*1024*1024))

        elif int(size_bytes/(1024*1024)) >0:
            print("Total Size : {:.2f} MB ({} bytes)".format(size_bytes/(1024*1024), size_bytes))
            return "{:.2f} MB".format(size_bytes/(1024*1024))

        elif int(size_bytes/(1024)) >0:
            print("Total Size : {:.2f} KB ({} bytes)".format(size_bytes/(1024), size_bytes))
            return "{:.2f} KB".format(size_bytes/(1024))

        else:
            print("Total Size : {} B ({} bytes)".format(size_bytes, size_bytes))
            return "{} B".format(size_bytes)


    def cal_total_size(self):

        with ThreadPoolExecutor(max_workers=7) as executor:

            futures = []
            for idx, url in enumerate(self.new_urls):
                #print(idx, 'URL : ',url)
                futures.append(executor.submit(self.fetch_size, idx, url))

            cumulative =0
            for future in as_completed(futures):
                cumulative += future.result()
            #print("Cumulative Size : {}\n".format(cumulative))
            return cumulative


    def fetch_urls(self, idx, url):
        ''' Save the urls to the disk'''

        req = urllib.request.urlopen(url)
        print(os.path.basename(url))
        filename = urllib.parse.unquote(os.path.basename(url))
        filename = filename.replace("/","-")
        filename = filename.replace("?","-")

        #print("Thread : {}".format(threading.current_thread().name))
        print("{}STARTED{} : {thread} => {filename}\n".format(Fore.RED, Style.RESET_ALL, thread=threading.current_thread().name ,filename=filename))

        with open(os.path.join(self.output_dir, filename), 'wb') as file_handler:

            prev_time = time.time()
            curr_size =0
            while True:
                chunk = req.read(1024)
                if not chunk:
                    break
                #print(sys.getsizeof(chunk))
                file_handler.write(chunk)
                curr_size += sys.getsizeof(chunk)

                with lock:
                    self.url_size[idx][1] = curr_size

                curr_time = time.time()
                if curr_time - prev_time >= 3:
                    print("{}{} Downloading {} {} : {} -->> {:.2f} %\n".format(Fore.RED,Back.CYAN,Style.RESET_ALL,threading.current_thread().name, filename, (curr_size/self.url_size[idx][2])*100 ))
                    prev_time = curr_time

        return "{}{} DONE {}: {thread} => {filename}\n".format(Fore.RED,Back.GREEN,Style.RESET_ALL, thread=threading.current_thread().name ,filename=filename)


    def download_urls(self):

        # Create temp and output paths based on where the executable is located
        self.base_dir = os.path.dirname(os.path.realpath(__file__))
        self.output_dir = os.path.join(self.base_dir, "output")

        if os.path.exists(self.output_dir)==False:
            os.mkdir(self.output_dir)

        with ThreadPoolExecutor(max_workers=7) as executor:

            futures = [executor.submit(self.fetch_urls, idx, url) for idx, url in enumerate(self.new_urls)]
            for future in as_completed(futures):
                print(future.result())

        print('======')

    def go(self):

        #Check for the entire size of downloads and check with user
        total_size_bytes = self.cal_total_size()
        total_size = self.print_relative_size(total_size_bytes)

        for idx, ele in self.url_size.items():
            print(" {} => {:.2f}MB : {} :: {:.2f}%".format(ele[0], ele[2]/(1024*1024), ele[1], (ele[1]/ele[2])*100))

        option =''
        while option not in ('Y', 'N'):
            option = input("\n"+Fore.RED+total_size+Style.RESET_ALL+" of Data required. Do you want to continue ? "+Back.RED+"[Y/N]"+Style.RESET_ALL+" : ")

            if option not in ('Y', 'N'):
                print("Incorrect option! Choose 'Y' or 'N'")

        #Don't proceed to donload if user opts out
        if option == 'N':
            print('Got it! Exiting ...')
            exit()

        print("Proceed to Download ....")
        #Proceed ahead to download the urls

        self.download_urls()

        for idx, ele in self.url_size.items():
            print(" {} => {:.2f}MB : {} :: {:.2f}%".format(ele[0], ele[2]/(1024*1024), ele[1], (ele[1]/ele[2])*100))

if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument("-u", "--urls", required=True, help=" File containing urls list")
    args = vars(ap.parse_args())

    if args["urls"]== "":
        print("Please enter a valid path to urls file")
        exit(1)
        
    slogg = Slogger(args["urls"])
    slogg.go()
