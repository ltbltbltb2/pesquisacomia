"""Fail-closed privacy checks. Private rules are never kept in this repository."""
import argparse, hashlib, html, json, os, re, subprocess, sys, unicodedata
from pathlib import Path
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
    def pdf(self, path):
        with fitz.open(path) as doc:
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
        self.binary(path.read_bytes(),path.name+': bytes')
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
            if path.suffix in {'.pdf','.png','.jpg','.jpeg','.woff','.woff2'}:
                if approved.get(path.name)!=hashlib.sha256(path.read_bytes()).hexdigest():
                    self.failures.add(path.name+': media requires a fresh privacy review')
            if path.suffix=='.pdf':self.pdf(path)
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
