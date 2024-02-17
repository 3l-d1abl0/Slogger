#!/usr/bin/python3
import os
import sys
import time
import argparse
import threading

from datetime import datetime
import asyncio


from goasync import coroutines
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

    def get_urls(self):

        #have the Output folder
        self.base_dir = os.path.dirname(os.path.realpath(__file__))
        self.output_dir = os.path.join(self.base_dir, "output")

        if os.path.exists(self.output_dir)==False:
            os.mkdir(self.output_dir)


        asyncio.run(coroutines.get_urls(self.output_dir, self.new_urls, self.url_size))

        print("Done ! Exiting !")



    def go(self):

        start = datetime.now()
        
        size_list = asyncio.run(coroutines.cal_total_size(self.urls, self.url_size))

        total_size_bytes = sum(size_list)
        if(total_size_bytes <= 0):
            print("[{}ERROR{}] {}{}{}".format(Fore.RED, Style.RESET_ALL, Fore.RED, "Unable to fetch Data !", Style.RESET_ALL))
            return
        
        total_size = self.print_relative_size(total_size_bytes)
        
        for idx, ele in self.url_size.items():
            print("[{}INFO{}] {} [{}{:.2f}MB{}]".format(Fore.GREEN, Style.RESET_ALL, ele[0], Fore.GREEN, ele[2]/(1024*1024), Style.RESET_ALL))

        option =''
        while option not in ('Y', 'N'):
            option = input("\n"+Fore.RED+total_size+Style.RESET_ALL+" of Data required. Do you want to continue ? "+Back.RED+"[Y/N]"+Style.RESET_ALL+" : ")

            if option not in ('Y', 'N'):
                print("Incorrect option!")
                print(f"You entered '{option}' You Choose 'Y' or 'N'")

        #Don't proceed to donload if user opts out
        if option == 'N':
            print('Got it! Exiting ...')
            exit()

        #Proceed ahead to download the urls
        print("Proceeding to fetch Urls ... ")
        sys.stdout.flush()
        
        
        self.get_urls()


if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument("-u", "--urls", required=True, help=" File containing urls list")
    args = vars(ap.parse_args())

    if args["urls"]== "":
        print("Please enter a valid path to urls file")
        exit(1)
        
    slogg = Slogger(args["urls"])
    slogg.go()
