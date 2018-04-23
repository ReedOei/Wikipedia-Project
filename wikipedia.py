import urllib2
import re
import sys
import ast

import datetime

from HTMLParser import HTMLParser
import os
from os import walk

import utility
import webutil

reload(sys)
sys.setdefaultencoding("utf-8")

IGNORE_BEGINNINGS = ['/wiki/Category', '/wiki/Talk', '/wiki/Special', '/wiki/User',
                     '/wiki/Template', '/w/index.php?', '/wiki/File', '/wiki/Portal',
                     '/wiki/Wikipedia', '/wiki/Help']

class LogParser:
    def __init__(self, directory = "none"):
        if not (directory == "none"):
            self.parseFiles(directory)

        self.directory = directory
        self.result = []

    def getFiles(self, directory):
        for (dirpath, dirnames, filenames) in walk(directory):
            for fname in filenames:
                yield os.path.join(dirpath, fname)

    def getContents(self, files, directory):
        contents = ""

        for i in files:
            with open(directory + i) as f:
                contents += f.read()

        return contents

    def clear(self):
        self.result = []

    def parseFile(self, fileName):
        contents = ""

        with open(fileName) as f:
            contents = f.read()

        if not contents.startswith('[['):
            for line in contents.split('\n'):
                self.result.append(ast.literal_eval(line))
        else:
            result = ast.literal_eval(contents)

            self.result += result

    def parseFiles(self, directory):
        self.clear()

        files = self.getFiles(directory)

        files = filter(lambda n: not n[0].startswith("."), files)

        self.result = []

        try:
            for fname in files:
                self.parseFile(fname)
        except SyntaxError as e:
            print(str(e))

        counts = [len(i) for i in self.result]

        while 395 in counts:
            counts = [len(i) for i in self.result]

            if 395 in counts:
                del self.result[counts.index(395)]

    def maxes(self):
        max_n = self.max_count()

        return [i for i in self.result if len(i) >= max_n]

    def mins(self):
        min_n = self.min_count()

        return [i for i in self.result if len(i) <= min_n]

    def max_count(self):
        return max([len(i) for i in self.result])

    def min_count(self):
        return min([len(i) for i in self.result])

    def get_max(self):
        return self.result[[len(i) for i in self.result].index(self.max_count())]

    def get_min(self):
        return self.result[[len(i) for i in self.result].index(self.min_count())]

    def filter(self, f):
        return [i for i in self.result if f(i)]

    def median(self):
        sorted_results = sorted(self.result, key = lambda n: len(n))

        answer = len(sorted_results[len(sorted_results) / 2])

        if len(self.result) % 2 == 0:
            answer += len(sorted_results[len(sorted_results) / 2 - 1])
            answer = answer / 2

        return answer

    def mode(self):
        counted_results = []
        counted_counts = []

        for i in self.result:
            try:
                counted_counts[counted_results.index(len(i))] += 1
            except:
                counted_results.append(len(i))
                counted_counts.append(1)

        return counted_results[counted_counts.index(max(counted_counts))]

    def mean(self):
        return float(sum([len(i) for i in self.result])) / float(len(self.result))

class WikipediaTracer:
    def __init__(self, target=None, source=None):
        self.cache = {}

        if target == None:
            self.target = '/wiki/Philosophy'
        else:
            self.target = target

        if source == None:
            self.source = 'Special:Random'
        else:
            self.source = source

        self.articles = 0

    def set_target(self, target):
        if not target.startswith('/wiki/'):
            self.target = '/wiki/' + target.replace(' ', '_')
        else:
            self.target = target

        print('Setting target to \'{}\''.format(self.target))

    def set_source(self, source):
        if not source.startswith('/wiki/'):
            self.source = '/wiki/' + source.replace(' ', '_')
        else:
            self.source = source

        print('Setting source to \'{}\''.format(self.source))

    def offloadCache(self, fileName):
        with open(fileName, "w") as f:
            for i, (key, value) in enumerate(self.cache.items()):
                utility.show_bar(i, len(self.cache), message='Offloading cache (\'{}\'): '.format(fileName))
                f.write(str((key, value)) + '\n')

        print('')

    def mergeCaches(self, fileNames, new_name=None):
        print('Merging caches.')
        caches = []

        print('Loading caches.')
        for i, fileName in enumerate(fileNames):
            with open(fileName) as f:
                result = f.read()

                cache = {}

                # It's the new format, with each line being one
                lines = result.split('\n')

                for lineno, line in enumerate(lines):
                    try:
                        utility.show_bar(lineno, len(lines), message='Loading cache ({} of {}): '.format(i + 1, len(fileNames)))
                        url, history = ast.literal_eval(line)

                        if isinstance(history, list):
                            cache[url] = history[0]
                            print(history, cache[url])
                        else:
                            cache[url] = history
                    except:
                        pass

                caches.append(cache)

                print('')

        if len(caches) >  0:
            # Save some time by just having everything in the first cache
            self.cache = dict(caches[0])

            total_done = 0
            total_included = 0
            total_entries = sum(map(lambda cache: len(cache), caches[1:]))

            for other in caches[1:]:
                for entry in other:
                    utility.show_bar(total_done, total_entries, message='Merging ({} of {} included): '.format(total_included, total_done))
                    if not entry in self.cache:
                        self.cache[entry] = other[entry]
                        total_included += 1

                    total_done += 1

            print('')

            if new_name != None:
                print('Finished merging caches, writing out our new cache to \'{}\''.format(new_name))

                for fileName in fileNames:
                    os.remove(fileName)
                self.offloadCache(new_name)

    def readCache(self, fileName):
        self.cache = []

        with open(fileName) as f:
            self.cache = ast.literal_eval(f.read())

    #Give a list of files and build the cache from those
    def buildCacheFromFiles(self, fileNames, directory = "", extension = ""):
        histories = LogParser()

        for i in fileNames:
            histories.parseFile(i + extension, directory)

        self.buildCache(histories)

    #Give a directory, parse all the files in it, then build the cache from those
    def buildCacheFromDirectory(self, directory):
        histories = LogParser()
        histories.parseFiles(directory)

        self.buildCache(histories)

    def buildCache(self, histories):
        print("Caching " + str(len(histories.result)) + " page traces.")

        for i, history in enumerate(histories.result):
            utility.show_bar(i, len(histories.result), message='Building cache: ')
            self.addToCache(history)

        print('')

    def addToCache(self, history):
        for i, href in enumerate(history):
            if i + 1 < len(history):
                if not href in self.cache:
                    self.cache[href] = history[i + 1]

    def writeToFile(self, fileName, n, output):
        with open(fileName + str(n / 1000) + ".txt", "w") as f:
            f.write(output)

    def infiniteSearch(self, fileName):
        n = 0

        output = []

        while True:
            print("Article Number: " + str(n))
            print("Cache Size: " +  str(len(self.cache)))
            try:
                result = self.find(self.source)

                output.append(result)
            except KeyboardInterrupt:
                print("Cancelled operation on article: " + str(n))
                print("Writing remaining output to log.")

                self.writeToFile(fileName, n, str(output))
                output = ""

                break
            except Exception as e:
                print("Failed!")
                print(e)
            n += 1

            if n % 1000 == 0:
                self.writeToFile(fileName, n, str(output))
                output = []

    def find(self, start=None, verbose=2, dirname=None):
        self.articles += 1

        if start != None:
            href = start
        else:
            href = self.source

        if not href.startswith("/wiki/"):
            href = '/wiki/' + href.replace(" ", "_")

        history = [href]

        while href != self.target:
            links = webutil.get_links("http://en.wikipedia.org" + href)
            links = filter(lambda link: link.in_paragraph or link.in_list, links)
            links = filter(lambda link: 'mw-content-ltr' in link.divs and not 'catlinks' in link.divs, links)
            links = filter(lambda link: not link.in_table and not link.in_tr and not link.in_parentheses, links)
            links = filter(lambda link: not any(map(lambda beginning: link.href.startswith(beginning), IGNORE_BEGINNINGS)), links)
            links = filter(lambda link: not link.href.startswith('#') and not 'cite_note' in link.href, links) # We don't want any cite notes and such
            links = filter(lambda link: link.href.startswith('/wiki/'), links)

            href = ''
            for link in links:
                if not link.href in history:
                    href = link.href
                    break

            history.append(href)

            if verbose > 1:
                print('{}: http://en.wikipedia.org{}'.format(len(history), href))

            if href in self.cache:
                while href != self.target:
                    href = self.cache[href]
                    history.append(href)

                    if verbose > 1:
                        print('http://en.wikipedia.org' + href)

                if dirname != None:
                    with open(dirname + str(self.articles / 1000) + '.txt', 'a') as f:
                        f.write(str(history) + '\n')

                self.addToCache(history)
                return history

            if href == self.target:
                if dirname != None:
                    with open(dirname + str(self.articles / 1000) + '.txt', 'a') as f:
                        f.write(str(history) + '\n')

                self.addToCache(history)
                return history
            elif href == '':
                raise Exception('No more links to follow for {}, ending search.'.format(start))

Tracer = WikipediaTracer()
Parser = LogParser()

if __name__ == '__main__':
    args = utility.command_line_args(sys.argv)

    if 'build-cache' in args:
        Tracer.buildCacheFromDirectory(args['build-cache'])

    if 'target' in args:
        Tracer.set_target(args['target'])

    if 'source' in args:
        Tracer.set_source(args['source'])

    if 'infinite' in args or 'infinite' in args['argv']:
        now = datetime.datetime.now()
        date_string = '{}-{}-{}'.format(now.year, now.month, now.day)
        time_string = '{}-{}-{}'.format(now.hour, now.minute, now.second)
        try:
            os.mkdir('logs/{}'.format(date_string))
        except OSError:
            pass

        os.mkdir('logs/{}/{}/'.format(date_string, time_string))
        Tracer.infiniteSearch('logs/{}/{}/'.format(date_string, time_string))
    elif 'search' in args or 'find' in args:
        Tracer.find()

