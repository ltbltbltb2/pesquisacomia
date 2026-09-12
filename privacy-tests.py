"""Synthetic adversarial tests; no real personal identifiers in test fixtures."""
import tempfile, unittest, zipfile, stat, struct, zlib
from pathlib import Path
import importlib.util
import pymupdf as fitz

spec=importlib.util.spec_from_file_location('privacy_check',Path(__file__).with_name('privacy-check.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PrivacyTests(unittest.TestCase):
    def test_policy_required(self):
        for value in [None,[],['']]:
            with self.assertRaises(ValueError):module.Check(value)
    def test_obfuscated_text(self):
        for text in ['Example Confidential Person','EXAMPLE\nCONFIDENTIAL PERSON','Example%20Confidential%20Person','Example&#32;Confidential&#32;Person']:
            c=module.Check(['Example Confidential Person']);c.text(text,'test');self.assertTrue(c.failures)
    def test_email_and_local_paths(self):
        for value in ['someone'+'@'+'example.org','/'+'home/'+'synthetic/Documents/test.txt','file:'+'///'+'private/example.pdf']:
            c=module.Check(['fictional-sensitive-marker']);c.text(value,'test');self.assertTrue(c.failures)
    def test_noreply(self):
        c=module.Check(['fictional-sensitive-marker']);c.text('123+publicuser@users.noreply.github.com noreply@github.com','test');self.assertFalse(c.failures)
    def test_xmp_with_empty_info_author(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.pdf';d=fitz.open();d.new_page().insert_text((72,72),'Public scientific content')
            d.set_metadata({'author':''});d.set_xml_metadata('<x:xmpmeta xmlns:x="adobe:ns:meta/"><creator>Example Confidential Person</creator></x:xmpmeta>');d.save(p)
            c=module.Check(['Example Confidential Person']);c.pdf(p);self.assertTrue(any('metadata' in s for s in c.failures))
    def test_page_text(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.pdf';d=fitz.open();d.new_page().insert_text((72,72),'Example Confidential Person');d.save(p)
            c=module.Check(['Example Confidential Person']);c.pdf(p);self.assertTrue(any('page' in s for s in c.failures))
    def test_links_and_attachments(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.pdf';d=fitz.open();page=d.new_page();page.insert_text((72,72),'Public text');page.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(70,60,140,80),'uri':'mailto:someone'+'@'+'example.org'});d.embfile_add('sample.txt',b'private fixture');d.save(p)
            c=module.Check(['fictional-sensitive-marker']);c.pdf(p);self.assertTrue(any('links' in s for s in c.failures));self.assertTrue(any('attachments' in s for s in c.failures))
    def inspect_zip(self, name, payload, attributes=None):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.zip'
            with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:
                item=zipfile.ZipInfo(name)
                if attributes is not None:item.external_attr=attributes
                z.writestr(item,payload)
            c=module.Check(['fictional-sensitive-marker']);c.archive(p);return c
    def test_archive_text(self):
        self.assertFalse(self.inspect_zip('package/readme.md',b'Public documentation').failures)
        self.assertTrue(self.inspect_zip('package/readme.md',b'fictional-sensitive-marker').failures)
    def test_archive_pdf_metadata(self):
        with fitz.open() as doc:
            doc.new_page();doc.set_xml_metadata('<creator>fictional-sensitive-marker</creator>')
            self.assertTrue(self.inspect_zip('package/paper.pdf',doc.tobytes()).failures)
    def test_archive_paths_and_types(self):
        for name in ['../readme.md','/readme.md','package/../readme.md','package\\readme.md','package/inner.zip','package/raw/data.csv','package/.git/config.txt']:
            with self.subTest(name=name),self.assertRaises(ValueError):self.inspect_zip(name,b'Public text')
        with self.assertRaises(ValueError):self.inspect_zip('package/link.txt',b'target',(stat.S_IFLNK|0o777)<<16)
    def test_archive_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('readme.md',b'one')
                with self.assertWarns(UserWarning):z.writestr('readme.md',b'two')
            with self.assertRaises(ValueError):module.Check(['fictional-sensitive-marker']).archive(p)
    def test_archive_expansion_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.zip'
            with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('readme.md',b'x'*(32*1024*1024+1))
            with self.assertRaises(ValueError):module.Check(['fictional-sensitive-marker']).archive(p)
    def test_archive_compressed_png_metadata(self):
        payload=b'Comment\0\0'+zlib.compress(b'fictional-sensitive-marker')
        chunk=struct.pack('>I',len(payload))+b'zTXt'+payload+b'\0'*4
        self.assertTrue(self.inspect_zip('package/figure.png',b'\x89PNG\r\n\x1a\n'+chunk).failures)

if __name__=='__main__':unittest.main()
