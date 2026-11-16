"""Shared static navigation for the website and generated validation page."""
import re

def apply_shell(page, prefix='../', current=''):
    logo=f'{prefix}assets/topicllm-mark.svg'
    links=[('app/','Explore demo','app'),('paper/','Method','paper'),('reproduce/','Fork + reproduce','reproduce')]
    navigation=''.join(f'<a href="{prefix}{href}"'+(' aria-current="page"' if key==current else '')+f'>{label}</a>' for href,label,key in links)
    header=f'''<header class="topbar"><div class="wrap"><a class="brand" href="{prefix}" aria-label="TopicLLM home"><svg viewBox="0 0 64 64" aria-hidden="true"><use href="{logo}#mark"/></svg><b>TopicLLM</b></a><button class="menu-toggle" data-menu aria-controls="platform-nav" aria-expanded="false" type="button">Menu</button><nav class="topnav" id="platform-nav" aria-label="Main navigation">{navigation}<a class="repo-link" href="https://github.com/jethomasphd/TopicLLM">GitHub ↗</a></nav><button class="theme-toggle" type="button" aria-label="Toggle light and dark theme" data-platform-theme><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></button></div></header>'''
    if re.search(r'<header\b',page):page=re.sub(r'<header\b.*?</header>',lambda _:header,page,count=1,flags=re.S)
    else:page=page.replace('<body>','<body>'+header,1)
    page=page.replace('assets/sigil.svg','assets/topicllm-mark.svg')
    if 'platform.css' not in page:
        head=f'''<link rel="stylesheet" href="{prefix}platform.css"><link rel="icon" href="{logo}" type="image/svg+xml"><script>try{{const theme=localStorage.getItem('topicllm-theme');if(theme)document.documentElement.dataset.theme=theme;}}catch{{}}</script><script type="module" src="{prefix}js/platform.js"></script>'''
        page=page.replace('</head>',head+'</head>',1)
    return page
