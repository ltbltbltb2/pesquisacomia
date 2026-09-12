"""Fail-closed privacy checks. Private rules are never kept in this repository."""
import argparse, hashlib, html, json, os, re, stat, struct, subprocess, sys, unicodedata, zipfile, zlib
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
import pymupdf as fitz

def normalize(text):
    text=html.unescape(unquote(text))
    return ''.join(c for c in unicodedata.normalize('NFKD',text).casefold() if not unicodedata.combining(c))

class Check:
    def __init__(self, terms):
        if not isinstance(terms,list) or not terms or any(not isinstance(t,str) or len(t)<3 for t in terms):
            raise ValueError('Private privacy policy is missing or invalid')
        self.terms=[normalize(t) for t in terms]
        self.byte_terms=[t.encode(enc) for t in terms for enc in ('utf-8','utf-16-be','utf-16-le','latin1')]
        self.failures=set(); self.pages=0; self.objects=0
    def text(self, text, location):
        n=normalize(text); compact=re.sub(r'\s+','',n)
        if any(t in n or re.sub(r'\s+','',t) in compact for t in self.terms):
            self.failures.add(location+': private identifier')
        for email in re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}',n):
            if not email.endswith('@users.noreply.github.com') and email!='noreply@github.com':
                self.failures.add(location+': non-publication email')
        if re.search(r'(?:file:///[a-z]|/(?:home|users)/[\w.-]+/|[a-z]:\\users\\[\w.-]+\\)',n):
            self.failures.add(location+': personal filesystem path')
    def binary(self, raw, location):
        lower=raw.lower()
        if any(t.lower() in lower for t in self.byte_terms):self.failures.add(location+': embedded private identifier')
    def pdf(self, path, raw=None):
        with (fitz.open(path) if raw is None else fitz.open(stream=raw,filetype='pdf')) as doc:
            if doc.is_encrypted or not doc.page_count:raise ValueError('PDF cannot be completely inspected')
            if doc.embfile_count():self.failures.add(path.name+': embedded attachments require review')
            self.text(json.dumps(doc.metadata,ensure_ascii=False)+doc.get_xml_metadata(),path.name+': metadata')
            for page in doc:
                self.pages+=1
                self.text(page.get_text(),path.name+': page '+str(page.number+1))
                self.text(str(page.get_links()),path.name+': links')
                for a in page.annots() or []:self.text(str(a.info),path.name+': annotation')
                for w in page.widgets() or []:self.text(str(w.field_name)+str(w.field_value),path.name+': field')
            for x in range(1,doc.xref_length()):
                self.objects+=1
                obj=doc.xref_object(x,compressed=False);self.text(obj,path.name+': object')
                for h in re.findall(r'(?<!<)<([0-9a-fA-F\s]+)>(?!>)',obj):
                    try:b=bytes.fromhex(h)
                    except ValueError:continue
                    self.text(b.decode('utf-16-be','ignore'),path.name+': encoded object')
                if doc.xref_is_stream(x):self.binary(doc.xref_stream(x),path.name+': stream')
        self.binary(path.read_bytes() if raw is None else raw,path.name+': bytes')
    def png(self, raw, location):
        self.binary(raw,location)
        if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG')
        pos=8
        def inflate(data):
            obj=zlib.decompressobj(); result=obj.decompress(data,1024*1024)
            if not obj.eof or obj.unused_data or obj.unconsumed_tail:raise ValueError('PNG metadata exceeds inspection limits')
            return result
        while pos+12<=len(raw):
            size=struct.unpack('>I',raw[pos:pos+4])[0]; kind=raw[pos+4:pos+8]
            if pos+12+size>len(raw):raise ValueError('Truncated PNG')
            data=raw[pos+8:pos+8+size];pos+=size+12
            if kind==b'tEXt':self.text(data.decode('latin1'),location+': PNG metadata')
            elif kind==b'zTXt':
                key,body=data.split(b'\0',1)
                if body[0]!=0:raise ValueError('Unknown PNG compression')
                self.text((key+b' '+inflate(body[1:])).decode('latin1'),location+': PNG metadata')
            elif kind==b'iTXt':
                key,body=data.split(b'\0',1); flag,method=body[:2];lang,translated,value=body[2:].split(b'\0',2)
                if flag not in (0,1) or method!=0:raise ValueError('Unknown PNG text format')
                self.text((key+b' '+lang+b' '+translated+b' '+(inflate(value) if flag else value)).decode('utf-8'),location+': PNG metadata')
    def archive(self, path):
        if path.stat().st_size>25*1024*1024:raise ValueError('Archive exceeds publication limit')
        with zipfile.ZipFile(path) as archive:
            entries=archive.infolist(); names=set(); total=0
            if not 0<len(entries)<=200:raise ValueError('Archive entry limit')
            for entry in entries:
                name=entry.filename; pure=PurePosixPath(name)
                if (not name or pure.is_absolute() or '\\' in name or any(x in ('','..','.') for x in name.rstrip('/').split('/'))
                    or ':' in name or name in names or any(ord(c)<32 for c in name)
                    or entry.flag_bits & 1 or stat.S_ISLNK(entry.external_attr>>16)):
                    raise ValueError('Unsafe archive entry')
                names.add(name);self.text(name,path.name+': member name')
                if any(x in {'.git','.venv','__pycache__','execucoes','00_governance','raw'} for x in pure.parts):
                    raise ValueError('Private or raw-data directory in public archive')
                if entry.is_dir():continue
                total+=entry.file_size
                if entry.file_size>32*1024*1024 or total>64*1024*1024:raise ValueError('Archive expansion limit')
                with archive.open(entry) as stream:raw=stream.read(32*1024*1024+1)
                if len(raw)!=entry.file_size:raise ValueError('Archive size mismatch')
                location=path.name+'::'+name
                if pure.suffix=='.pdf':self.pdf(Path(name),raw)
                elif pure.suffix=='.png':self.png(raw,location)
                elif pure.suffix in {'.py','.md','.txt','.json','.csv'}:self.text(raw.decode('utf-8'),location)
                else:raise ValueError('Archive member type requires review')
    def directory(self, root):
        approved=json.loads((root/'privacy-approved-media.json').read_text())
        if (root/'.git').exists():
            commit=subprocess.check_output(['git','log','-1','--format=%an <%ae>%n%cn <%ce>%n%B'],cwd=root,text=True)
            self.text(commit,'commit metadata')
        excluded={'.git','.github','.wrangler','node_modules','.privacy-deps','__pycache__'}
        for path in sorted(root.iterdir()):
            if path.name in excluded:continue
            if path.is_symlink() or not path.is_file():
                self.failures.add(path.name+': unexpected directory or symlink');continue
            self.text(path.name,'filename')
            if path.suffix in {'.pdf','.png','.jpg','.jpeg','.woff','.woff2','.zip'}:
                if approved.get(path.name)!=hashlib.sha256(path.read_bytes()).hexdigest():
                    self.failures.add(path.name+': media requires a fresh privacy review')
            if path.suffix=='.pdf':self.pdf(path)
            elif path.suffix=='.zip':self.archive(path)
            elif path.suffix in {'.png','.jpg','.jpeg','.woff','.woff2'}:self.binary(path.read_bytes(),path.name)
            else:self.text(path.read_text(encoding='utf-8'),path.name)
        manifest=json.loads((root/'manifesto-arquivos.json').read_text())
        names={x['file'] for x in manifest['files']}
        if names!={p.name for p in root.glob('*.pdf')}:raise ValueError('PDF inventory mismatch')
        for x in manifest['files']:
            raw=(root/x['file']).read_bytes()
            if len(raw)!=x['bytes'] or hashlib.sha256(raw).hexdigest()!=x['sha256']:raise ValueError('PDF integrity mismatch')
        config=json.loads((root/'wrangler.jsonc').read_text())
        if config.get('workers_dev') is not False or config.get('preview_urls') is not False:
            raise ValueError('Alternative public routes must be disabled')
        if config.get('build',{}).get('command')!='node privacy-build.mjs':raise ValueError('Deployment privacy gate missing')
        ignored=set((root/'.assetsignore').read_text().splitlines())
        required={'.git','.github','.wrangler','.privacy-deps','__pycache__','*.bundle','privacy-check.py','privacy-build.mjs','privacy-requirements.txt','privacy-tests.py','privacy-approved-media.json'}
        if not required<=ignored:raise ValueError('Build files must not be public assets')

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--policy',type=Path);a=p.parse_args()
    rules=os.environ.get('PRIVACY_DENY_TERMS')
    if a.policy:rules=a.policy.read_text()
    if not rules:
        result=subprocess.run(['git','config','--get','privacy.policyFile'],cwd=a.root,capture_output=True,text=True)
        if result.returncode==0:rules=Path(result.stdout.strip()).read_text()
    checker=Check(json.loads(rules or 'null'));checker.directory(a.root)
    if checker.failures:
        print('\n'.join(sorted(checker.failures)),file=sys.stderr);return 1
    print(json.dumps({'privacy':'passed','pdf_pages':checker.pages,'pdf_objects':checker.objects}));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        # Never print document text, policy values or exception strings into public build logs.
        print('Privacy verification could not finish ('+type(e).__name__+'). Publication blocked.',file=sys.stderr)
        sys.exit(1)
