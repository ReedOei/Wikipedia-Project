import utility

import ast
import random
import time

def command_line(args):
    result_log_dir = args.get('logs', 'logs/tests/')
    page_dir = args.get('page_dir', 'allpages/')
    show = args.get('show', 'last')
    show_num = args.get('show_num', 0)

    if not result_log_dir.endswith('/'):
        result_log_dir += '/'
    if not page_dir.endswith('/'):
        page_dir += '/'

    res = list(get_failed_pages(result_log_dir=result_log_dir, page_dir=page_dir))
    if show != None:
        if show == 'last':
            for i in xrange(int(show_num)):
                print(res[-i])
        elif show == 'first':
            for i in xrange(int(show_num)):
                print(res[i])
        elif show == 'random':
            for i in xrange(int(show_num)):
                print(random.choice(res))

    print('Total {} pages failed.'.format(len(res)))

def get_failed_pages(result_log_dir='logs/tests/', page_dir='allpages/'):
    n = 0
    files = utility.get_files(result_log_dir)
    total_lines = utility.lines_in_dir(result_log_dir)
    start_time = time.time()
    for fname in files:
        results = []
        with open(result_log_dir + fname, 'r') as f:
            results = f.read().split('\n')

        # Each line should be a dictionary containing the filename and the results
        results = filter(lambda i: len(i) > 0, results)
        results = map(ast.literal_eval, results)

        for i, (fname, fresults) in enumerate(map(lambda d: (d['fname'], d['result']), results)):
            utility.show_bar(n, total_lines, message='Checking fails ({} of {}): '.format(n, total_lines), start_time=start_time)
            n += 1

            try:
                lines = []
                with open(page_dir + fname, 'r') as f:
                    lines = f.read().split('\n')

                for line, result in zip(lines, fresults):
                    if not result and line != '/wiki/Main_Page':
                        yield (fname, line)
            except IOError:
                print('File \'{}\' not found.'.format(fname))
    print('')
if __name__ == '__main__':
    command_line(utility.command_line_args())
