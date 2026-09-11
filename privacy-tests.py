"""Synthetic adversarial tests; no real personal identifiers in test fixtures."""
import tempfile, unittest
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

if __name__=='__main__':unittest.main()
