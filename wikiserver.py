import utility

import socket
import threading
import SocketServer
import ast
import shutil
import shlex
import uuid
import os
import time

import wikipedia

# import get_failed_pages

# (client_path, server_path)
check_files = [('wikiserver.py', 'wikiserver.py'), ('wikipedia.py', 'wikipedia.py'), ('utility.py', '../Utility/utility.py'), ('webutil.py', '../Utility/webutil.py')]

class WikiClientHandler(SocketServer.StreamRequestHandler):
    def send(self, message, noprint=False):
        if not noprint:
            print('\tMessage: {}'.format(message))
        self.wfile.write(message + '\n')
        self.wfile.flush()

    def handle(self):
        print('Client connected.')
        client_id = ''
        while True:
            request_str = self.rfile.readline()

            if request_str == '':
                print('Client disconnected.')
                return

            request = utility.command_line_args(shlex.split(request_str))

            if 'client' in request:
                client_id = request['client']
            else:
                self.send('error fatal reason="no client id supplied!"')
                return

            print('Client: {}'.format(request_str))

            if 'check_files' in request:
                if not 'checksums' in request:
                    self.send('error reason="no checksums in request."')
                    continue

                print(request['checksums'])
                checksums = ast.literal_eval(request['checksums'])
                server_checksums = map(lambda (_, path): utility.md5(path), check_files)

                for client_checksum, server_checksum, (client_path, server_path) in zip(checksums, server_checksums, check_files):
                    if client_checksum != server_checksum:
                        self.send('update fname="{}"'.format(client_path))

                        contents = []
                        with open(server_path, 'r') as f:
                            contents = f.readlines()

                        for line in contents:
                            self.send(line[:-1], noprint=True)

                        self.send('<EOF>', noprint=True)

                self.send('done')
            elif 'next_file' in request:
                fname = self.server.get_next_file(client_id)

                self.send('success fname="{}"'.format(fname))

                contents = []
                with open(self.server.temp_directory + fname, 'r') as f:
                    contents = f.readlines()

                for line in contents:
                    self.send(line[:-1], noprint=True)

                self.send('<EOF>', noprint=True)
            elif 'finished' in request:
                if 'fname' in request:
                    fname = request['fname']
                else:
                    self.send('error reason="no filename included in request."')
                    continue

                if 'results' in request:
                    results = request['results']
                else:
                    self.send('error reason="no result included in request."')
                    continue

                self.server.finish_file(client_id, fname, ast.literal_eval(results))

                self.send('success')
            else:
                self.send('error fatal reason="no recognized command in request."')
                continue

class WikiServer:
    def __init__(self, host='localhost', port=60000, directory='allpages/', finished_directory='completed/', temp_directory='temp/', verify_directory='verify/', mode='new'):
        self.host = host
        self.port = port

        self.directory = directory
        self.finished_directory = finished_directory
        self.temp_directory = temp_directory
        self.verify_directory = verify_directory

        self.files = []
        self.verify_files = []
        self.in_use_files = []
        self.finished_files = []
        self.verify_files = []
        self.clients = {}

        self.client_stats = {}

        try:
            os.mkdir('logs/tests/')
        except:
            pass

        if mode == 'new':
            self.files = utility.get_files(self.directory)

            try:
                os.mkdir(self.finished_directory)
            except:
                pass

            try:
                os.mkdir(self.temp_directory)
            except:
                pass

            try:
                os.mkdir(self.verify_directory)
            except:
                pass

            for i, f in enumerate(self.files):
                utility.show_bar(i, len(self.files), number_limit=True, message='Copying to {}: '.format(self.temp_directory))
                shutil.copy(self.directory + f, self.temp_directory + f)

            print('')
        elif mode == 'continue':
            print('Loading temp files.')
            self.files = utility.get_files(self.temp_directory)

            print('Loading finished files.')
            self.finished_files = utility.get_files(self.finished_directory)
        elif mode == 'update':
            self.files = utility.get_files(self.temp_directory)
            self.finished_files = utility.get_files(self.finished_directory)

            all_files = self.files + self.finished_files

            check_files = utility.get_files(self.directory)
            for i, fname in enumerate(check_files):
                utility.show_bar(i, len(check_files), message='Updating files: ')
                if not fname in all_files:
                    shutil.copy(self.directory + fname, self.temp_directory + fname)

            print('')

            self.files = utility.get_files(self.temp_directory)

            # We should probably verify all the error files at some point.

        self.start_time = time.time()
        self.finished_since_start = 0

        def get_next_file(client):
            if not client in self.clients:
                self.clients[client] = []
                self.client_stats[client] = {}

            for fname in self.verify_files + self.files:
                if not fname in self.in_use_files:
                    self.in_use_files.append(fname)
                    self.clients[client].append(fname)
                    return fname

        def finish_file(client, fname, result):
            self.files.remove(fname)
            self.in_use_files.remove(fname)
            self.finished_files.append((fname, result))

            self.clients[client].remove(fname)

            if 'finished' in self.client_stats[client]:
                self.client_stats[client]['finished'] += 1
            else:
                self.client_stats[client]['finished'] = 1

            shutil.move(self.temp_directory + fname, self.finished_directory + fname)

            self.finished_since_start += 1
            elapsed = time.time() - self.start_time
            estimated_remaining = elapsed / self.finished_since_start * (len(self.files))

            print('Finished {} files so far. {} remaining.'.format(len(self.finished_files), utility.display_time(estimated_remaining)))

            utility.show_dict(self.client_stats)

            self.write_results_to_file('logs/tests/', fname, result)

        self.server = SocketServer.TCPServer((self.host, self.port), WikiClientHandler)

        # So the handlers can interact with us
        self.server.get_next_file = get_next_file
        self.server.finish_file = finish_file
        self.server.directory = directory
        self.server.finished_directory = finished_directory
        self.server.temp_directory = temp_directory

    def write_results_to_file(self, directory, fname, result):
        with open(directory + str(len(self.finished_files) / 1000) + '.txt', 'a') as f:
            output = {'fname': fname, 'result': result}
            f.write(str(output) + '\n')

    def start(self):
        print('Running server on {}:{}'.format(self.host, self.port))
        self.server.serve_forever()

class FatalException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class WikiClient:
    def __init__(self, host, port, nowrite=False, noupdate=False, target='Philosophy'):
        self.host = host
        self.port = port

        self.nowrite = nowrite
        self.noupdate = noupdate

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.working_file = ''

        self.Tracer = wikipedia.WikipediaTracer()
        self.Tracer.set_target(target)

        self.id = socket.gethostname()

        self.work_file = 'worker/{}-workfile.txt'.format(self.id)
        self.cache_file = 'worker/{}-cachefile.txt'.format(self.id)
        self.log_dir = 'worker/{}/'.format(self.id)
        self.fname = '' # The serverside name of the file we're working on
        self.results = []

        self.f = None

        try:
            os.mkdir(self.work_file.split('/')[0] + '/')
        except:
            pass

        try:
            os.mkdir(self.log_dir)
        except:
            pass

        cache_files = utility.get_files('worker/', search_re=r'cachefile')
        cache_files = map(lambda fname: 'worker/' + fname, cache_files)
        self.Tracer.mergeCaches(cache_files, new_name=self.cache_file)

        # In case we've run it with this computer before
        self.Tracer.articles = utility.lines_in_dir(self.log_dir)

    def recreate_socket(self):
        self.s.close()

        if self.f:
            self.f.close()

        self.f = None
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.host, self.port))
        self.f = self.s.makefile()

    def start(self):
        if not self.noupdate:
            self.check_updates()

        while True:
            try:
                work = self.get_work()
                result = self.do_work()
                self.Tracer.offloadCache(self.cache_file)
                self.send_result()
            except FatalException:
                self.s.close()
                break

    def check_updates(self):
        self.recreate_socket()

        print("Checking for updates.")
        checksums = map(lambda (path, _): utility.md5(path), check_files)
        self.send('check_files client="{}" checksums="{}"'.format(self.id, checksums))

        self.handle_response(mode='update')

    def handle_response(self, mode='get', updated=0):
        response_str = self.f.readline()
        response = utility.command_line_args(shlex.split(response_str))

        print('Received: {}'.format(response_str))

        error = False

        if 'error' in response:
            error = True
            if 'fatal' in response:
                if 'reason' in response:
                    raise FatalException('Fatal error occurred because: {}'.format(response['reason']))
                else:
                    raise FatalException('Fatal error occurred for an unknown reason.')
            else:
                if 'reason' in response:
                    print('Error: {}'.format(reason))
                else:
                    print('Error: An unknown error has occurred.')

        if mode == 'update':
            if 'done' in response:
                print('{} files updated.'.format(updated))
                # print('Closing socket.')
                self.s.shutdown(socket.SHUT_WR)
                self.s.close()

                if updated > 0:
                    raise Exception('Files were updated, please restart this program.')
            else:
                if 'update' in response:
                    receive_name = response['fname']

                    print('Receiving file \'{}\'.'.format(receive_name))

                    lines = 0
                    # Write out the file we received.
                    with open(receive_name, 'w') as receive_file:
                        while True:
                            next_line = self.f.readline()

                            if next_line != '<EOF>\n':
                                receive_file.write(next_line)
                            else:
                                break

                            lines += 1

                    print('Received {} lines.'.format(lines))

                    self.handle_response(mode='update', updated=updated + 1)
        else:
            if mode == 'get':
                self.fname = response['fname']

                print('Receiving file.')

                lines = 0
                # Write out the file we received.
                with open(self.work_file, 'w') as work_file:
                    while True:
                        next_line = self.f.readline()

                        if next_line != '<EOF>\n':
                            work_file.write(next_line)
                        else:
                            break

                        lines += 1

                print('Received {} lines.'.format(lines))

        if error or mode != 'update':
            # print('Closing socket.')
            self.s.shutdown(socket.SHUT_WR)
            self.s.close()

    def send(self, message):
        self.f.write(message + '\n')
        self.f.flush()

    def get_work(self):
        self.recreate_socket()
        print('Requesting next file.')
        self.send('next_file client="{}"'.format(self.id))

        self.handle_response(mode='get')

    def do_work(self):
        self.results = []

        failed = 0
        succeeded = 0

        lines = []
        with open(self.work_file, 'r') as work_file:
            lines = work_file.readlines()

        width, _ = utility.get_terminal_size()
        width -= 1

        start_time = time.time()
        for i, line in enumerate(lines):
            utility.show_bar(i, len(lines), width=width, start_time=start_time, message='{} of {}, {} fails. '.format(i, len(lines), failed))

            # Remove the newline first
            try:
                if self.nowrite:
                    history = self.Tracer.find(line[:-1], verbose=0)
                else:
                    history = self.Tracer.find(line[:-1], verbose=0, dirname=self.log_dir)

                self.results.append(True)
            except Exception as e:
                if not 'No more links to follow' in str(e):
                    print(e)

                self.results.append(False)

                failed += 1

        print('')

    def send_result(self):
        self.recreate_socket()
        print('Sending results.')
        self.send('finished client="{}" fname="{}" results="{}"'.format(self.id, self.fname, self.results))

        self.handle_response(mode='send')

def command_line(args):
    ip = args.get('ip', 'localhost')
    port = int(args.get('port', 60000))
    directory = args.get('directory', 'allpages/')
    temp_directory = args.get('temp_directory', 'temp/')
    finished_directory = args.get('finished_directory', 'completed/')
    target = args.get('target', 'Philosophy')
    mode = args.get('mode', 'new')
    noupdate = args.get('noupdate', False)
    nowrite = args.get('nowrite', False)

    if 'start' in args:
        s = WikiServer(ip, port, directory=directory, temp_directory=temp_directory, finished_directory=finished_directory, mode=mode)
        s.start()
    elif 'join' in args:
        client = WikiClient(ip, port, noupdate=noupdate, nowrite=nowrite, target=target)

        client.start()

if __name__ == '__main__':
    command_line(utility.command_line_args())
