import webutil
import utility

def check_link(link):
    if not link.href.startswith('/wiki/'):
        return False
    elif ':' in link.href:
        return False
    elif 'Main_Page' in link.href:
        return False

    return True

args = utility.command_line_args()
source = args.get('source', '/wiki/Special:AllPages')
history, matched_links = webutil.follow_links(source, check_link, link_text_pattern=r'Next page', link_prefix='http://en.wikipedia.org', fname='allpages', tries=6)
