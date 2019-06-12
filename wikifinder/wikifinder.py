import sys
import random
import cProfile

import utility
import webutil

IGNORE_BEGINNINGS = ['/wiki/Category', '/wiki/Talk', '/wiki/Special', '/wiki/User',
                     '/wiki/Template', '/w/index.php?', '/wiki/File', '/wiki/Portal',
                     '/wiki/Wikipedia', '/wiki/Help']

def average(l):
    return float(sum(l)) / float(len(l))

def count(l, verbose=0):
    res = {}
    for i, v in enumerate(l):
        if v in res:
            res[v] += 1
        else:
            res[v] = 1

        if verbose > 0:
            utility.show_bar(i, len(l), message='Counting: ')

    if verbose > 0:
        print('')

    return res

def valid_links(href, depth=0, curdepth=0, sample_n=-1):
    links = webutil.get_links("http://en.wikipedia.org" + href)
    links = filter(lambda link: 'mw-body-content' in link.divs and not 'catlinks' in link.divs and not 'reflist' in link.divs, links)
    links = filter(lambda link: not 'reflist columns references-column-width' in link.divs, links)
    links = filter(lambda link: not 'reference-text' in link.spans and not 'mw-cite-backlink' in link.spans, links)
    links = filter(lambda link: link.href != '/wiki/International_Standard_Book_Number', links)
    links = filter(lambda link: not any(map(lambda beginning: link.href.startswith(beginning), IGNORE_BEGINNINGS)), links)
    links = filter(lambda link: not link.href.startswith('#') and not 'cite_note' in link.href, links) # We don't want any cite notes and such
    links = filter(lambda link: link.href.startswith('/wiki/'), links)
    links = filter(lambda link: not 'Main_Page' in link.href, links)

    if depth <= 0:
        return map(lambda link: link.href, links)
    elif depth > 0:
        res = []
        if sample_n < 0:
            for i, link in enumerate(links):
                print('{}Getting links ({} of {}, {}) from {}'.format('\t' * curdepth, i + 1, len(links), len(res), link.href))
                res += valid_links(link.href, depth=depth - 1, curdepth=curdepth + 1, sample_n=sample_n)
        else:
            for i in xrange(sample_n):
                link = random.choice(links)
                print('{}Getting links ({} of {}, {}) from {}.'.format('\t' * curdepth, i + 1, sample_n, len(res), link.href))
                res += valid_links(link.href, depth=depth - 1, curdepth=curdepth + 1, sample_n=sample_n)
        return map(lambda link: link.href, links) + res

class Finder:
    def __init__(self, source, target, depth, sample_n):
        self.source = source
        self.target = target

        if not source.startswith('/wiki/'):
            self.source = '/wiki/' + source.replace(' ', '_')
        else:
            self.source = source

        if not target.startswith('/wiki/'):
            self.target = '/wiki/' + target.replace(' ', '_')
        else:
            self.target = target

        self.depth = depth
        self.sample_n = sample_n

        self.get_target_link_freq()

    def get_target_link_freq(self):
        print('Getting target links ({}).'.format(self.target))
        all_links = valid_links(self.target, depth=self.depth, sample_n=self.sample_n)
        print('Got {} links.'.format(len(all_links)))

        self.target_link_freq = count(all_links, verbose=1)
        self.target_link_freq = sorted(self.target_link_freq.items(), key=utility.snd)

        # The average frequency of the top links
        average_high_count = average(map(utility.snd, self.target_link_freq[-5:]))
        i = 0
        removed = 0
        while i < len(self.target_link_freq):
            href, n = self.target_link_freq[i]
            sys.stdout.write('\rCulling ({} removed, {} remaining).'.format(removed, len(self.target_link_freq)))
            sys.stdout.flush()

            # If this link appears less than 1% of the number of times as the average of the top 5
            if float(n) / average_high_count < 0.05 or n <= 1:
                self.target_link_freq.pop(i)
                removed += 1
            else:
                i += 1

        print('')
        print(self.target_link_freq)

    def score_page(self, href):
        return

    def estimate_distance(self, href):
        return

    def find(self, source=None):
        if source == None:
            source = self.source

        open_list = {}
        closed_list = {}
        href = source

        while href != self.target:
            links = valid_links(href)

            for link in links:
                open_list[link] = href

            # Score each page and choose the best one
            for link in open_list:
                return

def command_line(args):
    op = 'find'
    source = args.get('source', '/wiki/Special:Random')
    target = args.get('target', '/wiki/Philosophy')
    verbose = int(args.get('verbose', '1'))
    sample_n = int(args.get('n', '25'))
    depth = int(args.get('depth', '2'))

    f = Finder(source, target, depth, sample_n)
    res = f.find()
    print(res)

if __name__ == '__main__':
    args = utility.command_line_args()
    if 'profile' in args:
        cProfile.run('command_line(args)', sort='tottime')
    else:
        command_line(args)
