import {execFileSync} from 'node:child_process';
import path from 'node:path';
if (!process.env.PRIVACY_DENY_TERMS) throw new Error('Private privacy policy is required before deployment');
const python=process.env.PRIVACY_PYTHON || 'python3';
execFileSync(python,['-m','pip','install','--upgrade','--disable-pip-version-check','--require-hashes','--only-binary=:all:','--target','.privacy-deps','-r','privacy-requirements.txt'],{stdio:'inherit'});
execFileSync(python,['privacy-check.py','.'],{stdio:'inherit',env:{...process.env,PYTHONPATH:path.resolve('.privacy-deps')}});
